import os
from fastapi import FastAPI

app = FastAPI(title="Catalog Service")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "catalog-service")

PRODUCTS = [
    {"id": 1, "name": "Laptop", "price": 1200},
    {"id": 2, "name": "Keyboard", "price": 80},
    {"id": 3, "name": "Mouse", "price": 40},
]


@app.get("/health")
def health():
    return {"status": "ok", "instance": INSTANCE_NAME}


@app.get("/products")
def get_products():
    return {"instance": INSTANCE_NAME, "products": PRODUCTS}
