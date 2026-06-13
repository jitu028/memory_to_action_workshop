from fastapi import FastAPI, Response, HTTPException
import httpx
import time
import asyncio
import random

app = FastAPI(title="Payment API Service")

# Operational states
db_exhaustion_injected = False
order_api_url = "http://order-api:8001"

# Metrics
request_count = 0
error_count = 0
total_latency = 0.0

@app.middleware("http")
async def monitor_requests(request, call_next):
    global request_count, error_count, total_latency
    start_time = time.time()
    
    # Don't instrument metrics endpoint itself
    if request.url.path == "/metrics":
        return await call_next(request)
        
    request_count += 1
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            error_count += 1
        return response
    except Exception as e:
        error_count += 1
        raise e
    finally:
        latency = time.time() - start_time
        total_latency += latency

@app.get("/pay")
async def pay(amount: float, order_id: str):
    global db_exhaustion_injected
    
    # Simulate DB pool exhaustion latency
    if db_exhaustion_injected:
        # High latency (> 5s)
        await asyncio.sleep(random.uniform(5.0, 7.5))
        # 50% chance of failing with 503
        if random.random() > 0.5:
            raise HTTPException(status_code=503, detail="Database connection pool exhausted")

    # Call Order API dependency
    async with httpx.AsyncClient() as client:
        try:
            # Short timeout to simulate dependency failure quickly
            response = await client.get(f"{order_api_url}/order/{order_id}", timeout=2.0)
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to verify order details")
        except Exception:
            raise HTTPException(status_code=502, detail="Order API dependency is unavailable")

    # Success path
    return {"status": "success", "transaction_id": f"txn_{random.randint(100000, 999999)}"}

@app.post("/inject-db-exhaustion")
def inject_db_exhaustion(active: bool):
    global db_exhaustion_injected
    db_exhaustion_injected = active
    return {"message": f"Database pool exhaustion state set to {active}"}

@app.get("/status")
def status():
    return {
        "status": "healthy" if not db_exhaustion_injected else "degraded",
        "db_exhaustion_active": db_exhaustion_injected
    }

@app.get("/metrics")
def metrics():
    # Format Prometheus metrics manually
    p95_latency = 5.8 if db_exhaustion_injected else (total_latency / max(1, request_count))
    return Response(
        content=f"# HELP payment_api_requests_total Total number of payments requested\n"
                f"# TYPE payment_api_requests_total counter\n"
                f"payment_api_requests_total {request_count}\n"
                f"# HELP payment_api_errors_total Total number of payment errors\n"
                f"# TYPE payment_api_errors_total counter\n"
                f"payment_api_errors_total {error_count}\n"
                f"# HELP payment_api_latency_seconds Latency of payment requests in seconds\n"
                f"# TYPE payment_api_latency_seconds gauge\n"
                f"payment_api_latency_seconds{{quantile=\"0.95\"}} {p95_latency}\n"
                f"payment_api_latency_seconds{{quantile=\"0.50\"}} {p95_latency * 0.1}\n",
        media_type="text/plain"
    )
