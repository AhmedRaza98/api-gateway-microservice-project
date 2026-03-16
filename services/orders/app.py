import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Order Service")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "order-service")
FAIL_MODE = os.getenv("FAIL_MODE", "false").lower() == "true"
orders = []


class OrderRequest(BaseModel):
    product_id: int
    quantity: int


@app.get("/health")
def health():
    return {"status": "ok", "instance": INSTANCE_NAME, "fail_mode": FAIL_MODE}


@app.get("/all")
def get_orders():
    if FAIL_MODE:
        raise HTTPException(status_code=500, detail=f"{INSTANCE_NAME} is failing intentionally")
    return {"instance": INSTANCE_NAME, "orders": orders}


@app.post("/create")
def create_order(payload: OrderRequest):
    if FAIL_MODE:
        raise HTTPException(status_code=500, detail=f"{INSTANCE_NAME} is failing intentionally")

    order = {
        "id": len(orders) + 1,
        "product_id": payload.product_id,
        "quantity": payload.quantity,
        "instance": INSTANCE_NAME,
    }
    orders.append(order)
    return {"message": "order created", "order": order}
