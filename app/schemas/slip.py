from pydantic import BaseModel, Field

class Slip(BaseModel):   
    id: str
    # force slipKey to be slip_key in JSON
    slipKey: str = Field(None, alias="slipKey", max_length=200)
    marketID: str = Field(None, alias="marketID", max_length=100)
    vendorReservationID: str = Field(None, alias="vendorReservationID", max_length=200)

class SlipResponse(BaseModel):
    data: Slip