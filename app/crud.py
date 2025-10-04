from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from app.db.mongo import get_database
from app.core.config import settings

async def create_slip(slip_key: str, market_id: str, vendor_reservation_id: str) -> dict:
    """
    Create a new slip record
    
    Args:
        slip_key: The S3 key for the uploaded slip image
        market_id: The ID of the market
        vendor_reservation_id: The ID of the vendor reservation
        
    Returns:
        The newly created slip document
    """
    db = get_database()
    slip_collection = db[settings.MONGO_DB_SLIP]
    
    # Create the slip record
    slip_data = {
        "slipKey": slip_key,
        "marketID": market_id,
        "vendorReservationID": vendor_reservation_id
    }
    
    result = await slip_collection.insert_one(slip_data)
    
    # Fetch the created document
    created_slip = await slip_collection.find_one({"_id": result.inserted_id})
    created_slip["id"] = str(created_slip["_id"])
    
    return created_slip

async def get_slips_by_reservation_id(vendor_reservation_id: str) -> List[dict]:
    """
    Get all slip records associated with a specific reservation ID
    
    Args:
        vendor_reservation_id: The ID of the vendor reservation
        
    Returns:
        List of slip documents
    """
    db = get_database()
    slip_collection = db[settings.MONGO_DB_SLIP]
    
    # Query the collection
    cursor = slip_collection.find({"vendorReservationID": vendor_reservation_id})
    
    # Convert ObjectId to string for each document
    slips = []
    async for slip in cursor:
        slip["id"] = str(slip["_id"])
        slips.append(slip)
        
    return slips

async def get_slip_by_id(slip_id: str) -> Optional[dict]:
    """
    Get a slip record by its ID
    
    Args:
        slip_id: The ID of the slip to retrieve
        
    Returns:
        The slip document or None if not found
    """
    db = get_database()
    slip_collection = db[settings.MONGO_DB_SLIP]
    
    try:
        # Convert string ID to ObjectId
        object_id = ObjectId(slip_id)
        slip = await slip_collection.find_one({"_id": object_id})
        
        if slip:
            slip["id"] = str(slip["_id"])
            return slip
        return None
    except:
        return None

async def delete_slip(slip_id: str) -> bool:
    """
    Delete a slip record
    
    Args:
        slip_id: The ID of the slip to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    db = get_database()
    slip_collection = db[settings.MONGO_DB_SLIP]
    
    try:
        # Convert string ID to ObjectId
        object_id = ObjectId(slip_id)
        result = await slip_collection.delete_one({"_id": object_id})
        return result.deleted_count > 0
    except:
        return False
