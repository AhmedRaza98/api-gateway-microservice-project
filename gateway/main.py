import os
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="API Gateway")

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

SERVICES: Dict[str, List[str]] = {
    "auth": [os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")],
    "catalog": [u.strip() for u in os.getenv("CATALOG_SERVICE_URLS", "").split(",") if u.strip()],
    "orders": [u.strip() for u in os.getenv("ORDER_SERVICE_URLS", "").split(",") if u.strip()],
}

rr_indexes: Dict[str, int] = defaultdict(int)
rate_limit_store: Dict[str, deque] = defaultdict(deque)
metrics = {
    "requests_total": 0,
    "auth_failures": 0,
    "rate_limited": 0,
    "retries": 0,
    "failovers": 0,
}

circuit_breakers: Dict[str, Dict[str, float]] = {
    url: {"failures": 0, "open_until": 0.0} for service_urls in SERVICES.values() for url in service_urls
}
FAILURE_THRESHOLD = 2
CIRCUIT_OPEN_SECONDS = 15
REQUEST_TIMEOUT = 2.0


@app.middleware("http")
async def security_and_rate_limit(request: Request, call_next):
    metrics["requests_total"] += 1
    path = request.url.path

    if path not in {"/health", "/metrics"} and not path.startswith("/auth/"):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            metrics["auth_failures"] += 1
            return JSONResponse(status_code=401, content={"error": "Missing bearer token"})
        token = auth_header.split(" ", 1)[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            metrics["auth_failures"] += 1
            return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    timestamps = rate_limit_store[client_ip]
    while timestamps and now - timestamps[0] > RATE_LIMIT_WINDOW_SECONDS:
        timestamps.popleft()
    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        metrics["rate_limited"] += 1
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})
    timestamps.append(now)

    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok", "services": SERVICES}


@app.get("/metrics")
def get_metrics():
    return {
        "metrics": metrics,
        "circuit_breakers": circuit_breakers,
        "round_robin_indexes": dict(rr_indexes),
    }


async def proxy_request(service_name: str, path: str, request: Request) -> Response:
    targets = SERVICES.get(service_name, [])
    if not targets:
        raise HTTPException(status_code=500, detail=f"No targets configured for {service_name}")

    body = await request.body()
    query = f"?{request.url.query}" if request.url.query else ""
    method = request.method
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }

    tried = set()
    attempts = 0

    while attempts < len(targets):
        target = pick_target(service_name, tried)
        if not target:
            break
        tried.add(target)
        attempts += 1
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                upstream = f"{target}/{path}{query}"
                response = await client.request(method, upstream, headers=headers, content=body)
            if response.status_code >= 500:
                register_failure(target)
                metrics["retries"] += 1
                continue
            register_success(target)
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() != "content-length"},
                media_type=response.headers.get("content-type"),
            )
        except httpx.RequestError:
            register_failure(target)
            metrics["retries"] += 1
            continue

    metrics["failovers"] += 1
    return JSONResponse(status_code=503, content={"error": f"All {service_name} instances unavailable"})


def pick_target(service_name: str, tried: set) -> Optional[str]:
    candidates = SERVICES[service_name]
    if not candidates:
        return None

    for _ in range(len(candidates)):
        idx = rr_indexes[service_name] % len(candidates)
        rr_indexes[service_name] += 1
        candidate = candidates[idx]
        cb = circuit_breakers[candidate]
        if candidate in tried:
            continue
        if cb["open_until"] > time.time():
            continue
        return candidate
    return None


def register_failure(target: str) -> None:
    cb = circuit_breakers[target]
    cb["failures"] += 1
    if cb["failures"] >= FAILURE_THRESHOLD:
        cb["open_until"] = time.time() + CIRCUIT_OPEN_SECONDS


def register_success(target: str) -> None:
    cb = circuit_breakers[target]
    cb["failures"] = 0
    cb["open_until"] = 0.0


@app.api_route("/auth/{path:path}", methods=["GET", "POST"])
async def auth_proxy(path: str, request: Request):
    return await proxy_request("auth", path, request)


@app.api_route("/catalog/{path:path}", methods=["GET", "POST"])
async def catalog_proxy(path: str, request: Request):
    return await proxy_request("catalog", path, request)


@app.api_route("/orders/{path:path}", methods=["GET", "POST"])
async def orders_proxy(path: str, request: Request):
    return await proxy_request("orders", path, request)
