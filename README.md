# Slip Management Service

This service manages payment slips for the EIEI Marketplace.

## Features

- Upload payment slip images to S3
- Retrieve slip images by reservation ID
- Integration with RabbitMQ for notification to other services
- Update reservation statuses based on payment validation

## API Endpoints

### 1. GET `/slip/reservation/{reservation_id}`

Retrieves all slip images associated with a reservation.

**Response:**
```json
{
  "slip_urls": [
    "https://s3-url-to-slip-1",
    "https://s3-url-to-slip-2"
  ]
}
```

### 2. POST `/slip/create`

Upload a new payment slip.

**Request:**
- Form data with:
  - `slipFile`: The slip image file
  - `reservationId`: The ID of the vendor reservation
  - `marketId`: The ID of the market

**Response:**
```json
{
  "message": "Slip uploaded successfully",
  "id": "slip-id",
  "slipKey": "s3-key",
  "marketID": "market-id",
  "vendorReservationID": "reservation-id",
  "slip_url": "https://s3-url-to-slip"
}
```

### 3. POST `/slip/update-status`

Manually update a reservation status.

**Request:**
- Form data with:
  - `reservationId`: The ID of the reservation
  - `status`: The new status (one of: Application, WaitforPay, ValidateSlip, Merchant, Retire)

**Response:**
```json
{
  "message": "Reservation status updated to {status}"
}
```

## Data Schema

```
Slip:
  id: UUID (MongoDB ObjectID)
  slipKey: String (S3 key to access the image)
  marketID: UUID (Foreign Key to Market)
  vendorReservationID: UUID (Foreign Key to VendorReservation)
```

## Reservation Status Flow

1. Normal - Initial state (not related to this service)
2. Application - Vendor submitted application
3. WaitforPay - Accepted, waiting for payment
4. ValidateSlip - Payment slip submitted, waiting for validation
5. Merchant - Payment validated, reservation confirmed
6. Retire - Canceled or retired

## Running the Service

```bash
# With Docker
docker-compose up -d

# Without Docker
pip install -r requirements.txt
python main.py
```

## Environment Variables

See `.env.sample` for required environment variables.
