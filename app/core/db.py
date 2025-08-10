# app/core/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL

# 1) Buat engine sekali
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 2) Buat SessionLocal sekali
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3) Fungsi dependency untuk FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()