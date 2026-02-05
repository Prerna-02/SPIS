"""
SPIS Auth Service - Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Postgres
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "spis")
POSTGRES_USER = os.getenv("POSTGRES_USER", "spis_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "spis_dev_password")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Face Recognition
FACE_SIMILARITY_THRESHOLD = float(os.getenv("FACE_SIMILARITY_THRESHOLD", "0.6"))
FACE_REQUIRED = os.getenv("FACE_REQUIRED", "false").lower() == "true"

# Service
AUTH_PORT = int(os.getenv("AUTH_PORT", "8004"))
