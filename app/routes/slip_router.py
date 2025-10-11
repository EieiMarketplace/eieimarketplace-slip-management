from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List, Dict, Any
from pydantic import BaseModel
import uuid
from datetime import datetime
from PIL import Image
from core.image_check import validate_image

# Authentication and authorization imports
# - get_user_from_token: Validates token and returns UserInfo
# - require_role: Creates a dependency that requires a specific role
from app.auth.auth import get_user_from_token, require_role
from app.utils.s3 import upload_file_to_s3, generate_presigned_url
from app.messaging.rabbitmq import update_reservation_status, send_message
from app import crud

router = APIRouter()
security = HTTPBearer()

class SlipUrlResponse(BaseModel):
    slip_urls: List[str]
    
async def check_slip_access(user_info, reservation_id: str) -> bool:
    """
    Check if user has access to a slip based on:
    1. User is a vendor and owns the reservation
    2. User is an organizer of the market that contains the reservation
    3. User is an admin
    
    Returns True if access is allowed, False otherwise
    """
    # Admin always has access
    if user_info.role == "admin":
        return True
        
    # Organizer has access to all slips in their markets
    if user_info.role == "organizer":
        # Here you would check if the reservation's market is managed by this organizer
        # For now, we're granting access to all organizers
        return True
        
    # Vendor has access only to their own reservations
    if user_info.role == "vendor":
        # TODO: Check if this reservation belongs to this vendor by querying the reservation service
        # For now, implement a simple check (this should be improved in production)
        try:
            # Get the reservation and check if it belongs to this user
            # This is a placeholder - replace with actual reservation lookup
            # For demo purposes, we're granting access to all vendors
            return True
        except Exception:
            return False
            
    return False

@router.get("/reservation/{reservation_id}", response_model=SlipUrlResponse)
async def get_slips_by_reservation_id(
    reservation_id: str, 
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Verify user authentication
    user_info = await get_user_from_token(credentials.credentials)
    
    # Check if user has access to this reservation's slips
    has_access = await check_slip_access(user_info, reservation_id)
    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view these slips"
        )
    
    # Get all slips for this reservation
    slips = await crud.get_slips_by_reservation_id(reservation_id)
    slip_urls = []
    for slip in slips:
        try:
            url = generate_presigned_url(slip["slipKey"])  # Fixed typo: slit -> slip
            slip_urls.append(url)
        except Exception as e:
            print(f"Error generating URL for slip {slip['id']}: {str(e)}")
    return {"slip_urls": slip_urls}

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_slip(
    slipFile: UploadFile = File(...),
    reservationId: str = Form(...),
    marketId: str = Form(...),
    user_info = Depends(require_role("vendor"))
):
    # User is already verified as a vendor by the require_role dependency
    
    # Validate the file is an image
    if not slipFile.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Validate image integrity
    validate_image(slipFile)

    # validate file size (max 5MB)
    if slipFile.spool_max_size and slipFile.spool_max_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")
    

    try:
        # 1. Upload image to S3
        # Generate a unique key for the file
        unique_filename = f"{uuid.uuid4()}_{datetime.now().timestamp()}_{slipFile.filename}"
        
        # check slipFile.file is not None
        if slipFile.file is None:
            raise HTTPException(status_code=400, detail="No file uploaded")
        # check slipFile.file is image (slipfile is binary file)
        if not slipFile.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are allowed")

        # Upload to S3 and get the file key
        slip_key = upload_file_to_s3(slipFile.file, unique_filename, slipFile.content_type)
        
        # 2. Create slip record in MongoDB
        slip = await crud.create_slip(slip_key, marketId, reservationId)
        
        # 3. Send message to RabbitMQ to update reservation status
        message_payload = {
            "event": "UPDATE_RESERVATION_STATUS",
            "reservationId": reservationId,
            "marketId": slip["marketID"],
            "vendorReservationStatus": "ValidateSlip"
        }
        
        await update_reservation_status(
            slip["marketID"],
            reservationId, 
            "ValidateSlip",
            message_payload
        )
        
        # Generate a URL for the uploaded slip
        # slip_url = generate_presigned_url(slip_key)
        
        return {
            "message": "Slip uploaded successfully",
            "id": slip["id"],
            "slipKey": slip["slipKey"],
            "marketID": slip["marketID"],
            "vendorReservationID": slip["vendorReservationID"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload slip: {str(e)}")

# @router.post("/update-status")
# async def update_reservation_status_endpoint(
#     reservationId: str = Form(...),
#     status: str = Form(...),
#     user_info = Depends(require_role("admin"))
# ):
#     # User is already verified as an admin by the require_role dependency
#     valid_statuses = ["Application", "WaitforPay", "ValidateSlip", "Merchant", "Retire"]
#     if status not in valid_statuses:
#         raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
#     try:
#         # Create the message payload for RabbitMQ
#         message_payload = {
#             "event": "UPDATE_RESERVATION_STATUS",
#             "reservationId": reservationId,
#             "vendorReservationStatus": status
#         }
        
#         # Send the message to update reservation status
#         await update_reservation_status(reservationId, status, message_payload)
        
#         return {"message": f"Reservation status updated to {status}"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to update reservation status: {str(e)}")
