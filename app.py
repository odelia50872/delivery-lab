from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any

app = FastAPI()

# ----------------------------------------------------
# 1. Custom Exception Handlers (מחזיר error במקום detail)
# ----------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body or parameters"}
    )

# ----------------------------------------------------
# 2. In-memory Database
# ----------------------------------------------------
deliveries_db: Dict[int, Dict[str, Any]] = {}
current_id = 0

VALID_STATUSES = ["created", "in_transit", "delivered"]

# ----------------------------------------------------
# 3. Endpoints
# ----------------------------------------------------

# 1. Health
@app.get("/health")
def health():
    return {"status": "ok"}


# 2. Create Delivery
@app.post("/deliveries", status_code=201)
async def create_delivery(request: Request):
    global current_id
    
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")

    recipient = body.get("recipient")
    address = body.get("address")

    if not isinstance(recipient, str) or not recipient.strip():
        raise HTTPException(status_code=400, detail="Recipient must be a non-empty string")
    if not isinstance(address, str) or not address.strip():
        raise HTTPException(status_code=400, detail="Address must be a non-empty string")

    current_id += 1
    new_delivery = {
        "id": current_id,
        "recipient": recipient,
        "address": address,
        "status": "created"
    }
    deliveries_db[current_id] = new_delivery
    return new_delivery


# 5. List and Filter Deliveries
@app.get("/deliveries")
def list_deliveries(status: Optional[str] = None):
    if status is not None:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        return [d for d in deliveries_db.values() if d["status"] == status]
    return list(deliveries_db.values())


# 2. Get Delivery
@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    if delivery_id not in deliveries_db:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return deliveries_db[delivery_id]


# 4. Status Lifecycle Update
@app.patch("/deliveries/{delivery_id}/status")
async def update_status(delivery_id: int, request: Request):
    if delivery_id not in deliveries_db:
        raise HTTPException(status_code=404, detail="Delivery not found")
        
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")
        
    new_status = body.get("status")
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status value")

    current_status = deliveries_db[delivery_id]["status"]

    allowed_transitions = {
        "created": "in_transit",
        "in_transit": "delivered"
    }

    if allowed_transitions.get(current_status) != new_status:
        raise HTTPException(status_code=409, detail=f"Cannot transition from {current_status} to {new_status}")

    deliveries_db[delivery_id]["status"] = new_status
    return deliveries_db[delivery_id]


# 6. Delete Delivery
@app.delete("/deliveries/{delivery_id}")
def delete_delivery(delivery_id: int):
    if delivery_id not in deliveries_db:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if deliveries_db[delivery_id]["status"] != "created":
        raise HTTPException(status_code=409, detail="Can only delete deliveries with status 'created'")

    del deliveries_db[delivery_id]
    return Response(status_code=204)