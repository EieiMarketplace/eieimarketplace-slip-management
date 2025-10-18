 
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.routes.slip_router import router as slip_router
from app.db.mongo import close_mongo_connection, connect_to_mongo
from app.messaging.rabbitmq import get_rabbitmq_connection
from app.core.config import settings
import aio_pika

async def setup_rabbitmq():
    connection = await get_rabbitmq_connection()
    channel = await connection.channel()

    exchange = await channel.declare_exchange(
        "vendor_reservation",
        aio_pika.ExchangeType.TOPIC,
        durable=True
    )

    # สร้าง queue ที่จะรับ message จาก exchange
    queue = await channel.declare_queue(
        "reservation_status_queue",
        durable=True
    )

    # bind queue กับ exchange ตาม routing key
    await queue.bind(exchange, routing_key="reservation.status")

    print("✅ RabbitMQ exchange & queue created and bound successfully!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    await setup_rabbitmq()
    yield
    # Shutdown
    close_mongo_connection()
    
app = FastAPI(title="Eiei Slip Management", lifespan=lifespan)
list = [ 
       
        "http://localhost:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",settings.FRONTEND_URL],       
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],          
    allow_headers=["*"],          
)
 
 

app.include_router(slip_router, prefix="/slip", tags=["Reservations"])


async def serve_fastapi():
    config = uvicorn.Config(app, host="0.0.0.0", port=7004)
    server = uvicorn.Server(config)
    await server.serve()
    
async def main():
    await asyncio.gather(
        serve_fastapi(),
    )

if __name__ == "__main__":
    asyncio.run(main())