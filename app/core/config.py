from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # MongoDB settings
    MONGO_URL: str
    MONGO_DB: str
    MONGO_DB_SLIP: str = "slips"
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    REGION_NAME: str
    S3_BUCKET_NAME: str
    
    # RabbitMQ Configuration
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    
    # Service URLs
    AUTH_SERVICE_URL: str = "http://host.docker.internal:7001"
    MARKET_SERVICE_URL: str = "http://host.docker.internal:7002/markets"
    VENDOR_RESERVATION_SERVICE_URL: str = "http://host.docker.internal:7003"
    FRONTEND_URL:str="http://host.docker.internal:3000"
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()