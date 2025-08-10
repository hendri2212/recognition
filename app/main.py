from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from app.core.config import DATABASE_URL
# Import Base from a central base module
from app.models.base import Base
# Import models to register metadata
import app.models.user
import app.models.person

from app.api.endpoints.register import router as register_router
from app.api.endpoints.recognize import router as recognize_router

# Initialize FastAPI
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Atau ganti dengan ['http://localhost:8080']
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup: create tables from all models
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)

# Include API routers
app.include_router(register_router, prefix="")
app.include_router(recognize_router, prefix="")