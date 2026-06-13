from fastapi import FastAPI, HTTPException
import random

app = FastAPI(title="Order API Service")

@app.get("/order/{order_id}")
def get_order(order_id: str):
    # Simulate database lookups or order verification
    if order_id.startswith("err_"):
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_id": order_id,
        "status": "pending_payment",
        "items": [
            {"item_id": f"item_{random.randint(10, 99)}", "price": round(random.uniform(5.0, 150.0), 2)}
        ]
    }

@app.get("/healthz")
def healthz():
    return {"status": "healthy"}
