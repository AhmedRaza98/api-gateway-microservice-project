import os
import time

import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Auth Service")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "auth-service")

USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"},
}


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/health")
def health():
    return {"status": "ok", "instance": INSTANCE_NAME}


@app.post("/login")
def login(payload: LoginRequest):
    user = USERS.get(payload.username)
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {
            "sub": payload.username,
            "role": user["role"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer", "instance": INSTANCE_NAME}
