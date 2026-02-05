"""
SPIS Auth Service - FastAPI Application
=======================================
Authentication with password + optional face verification.

Endpoints:
- POST /auth/register - Create user account
- POST /auth/login - Login with password (+ optional face)
- POST /auth/logout - Clear session
- POST /auth/face/enroll - Save face embedding
- POST /auth/face/verify - Verify face
- GET /auth/me - Get current user
"""

from fastapi import FastAPI, HTTPException, Response, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncpg
import db
import auth as auth_utils
from config import FACE_SIMILARITY_THRESHOLD, FACE_REQUIRED

app = FastAPI(
    title="SPIS Auth Service",
    description="Authentication with password + optional face verification",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cookie settings
COOKIE_NAME = "spis_auth_token"
COOKIE_MAX_AGE = 60 * 60 * 24  # 24 hours


# ============================================================
# MODELS
# ============================================================

class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str
    face_image: Optional[str] = None  # base64


class FaceEnrollRequest(BaseModel):
    face_image: str  # base64


class FaceVerifyRequest(BaseModel):
    username: str
    face_image: str  # base64


class UserResponse(BaseModel):
    user_id: str
    username: str
    role: str
    has_face: bool


# ============================================================
# HELPERS
# ============================================================

def get_token_from_cookie(request: Request) -> Optional[str]:
    """Extract auth token from cookie."""
    return request.cookies.get(COOKIE_NAME)


async def get_current_user(request: Request) -> dict:
    """Get current authenticated user from cookie."""
    token = get_token_from_cookie(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = auth_utils.get_token_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# ============================================================
# ENDPOINTS
# ============================================================

@app.exception_handler(asyncpg.PostgresError)
async def postgres_exception_handler(request: Request, exc: asyncpg.PostgresError):
    """Handle Postgres errors gracefully."""
    print(f"[ERROR] Database error: {exc}")
    # unique_violation
    if isinstance(exc, asyncpg.UniqueViolationError):
        return JSONResponse(
            status_code=409,
            content={"detail": "Resource already exists (username conflict)"}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error occurred"}
    )

@app.exception_handler(OSError)
async def db_connection_handler(request: Request, exc: OSError):
    """Handle DB connection errors."""
    print(f"[ERROR] Connection error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Service unavailable: Database connection failed"}
    )

@app.get("/health")
async def health_check():
    try:
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "healthy", "service": "auth"}
    except Exception as e:
        print(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.post("/auth/register")
async def register(req: RegisterRequest):
    """Register new user with username + password."""
    print(f"[INFO] Registering user: {req.username}")
    try:
        # Check if username exists
        existing = await db.get_user_by_username(req.username)
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")
        
        # Hash password and create user
        password_hash = auth_utils.hash_password(req.password)
        try:
            user = await db.create_user(req.username, password_hash)
        except asyncpg.UniqueViolationError:
            # Race condition handling
            raise HTTPException(status_code=409, detail="Username already exists")
        
        print(f"[OK] User registered: {user['user_id']}")
        return {
            "message": "User registered successfully",
            "user_id": str(user["user_id"]),
            "username": user["username"]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/auth/login")
async def login(req: LoginRequest, response: Response, request: Request):
    """
    Login with username + password.
    Optionally verify face if provided and user has face enrolled.
    """
    client_ip = request.client.host if request.client else "unknown"
    print(f"[INFO] Login attempt: {req.username} from {client_ip}")
    
    try:
        # Get user
        user = await db.get_user_by_username(req.username)
        if not user:
            print(f"[ERROR] User not found: {req.username}")
            await db.log_login_event(None, False, "password", client_ip)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not auth_utils.verify_password(req.password, user["password_hash"]):
            print(f"[ERROR] Invalid password for: {req.username}")
            await db.log_login_event(str(user["user_id"]), False, "password", client_ip)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Optional face verification
        method = "password"
        face_verified = None
        
        if req.face_image and user.get("face_embedding"):
            try:
                import face as face_utils
                verified, similarity = face_utils.verify_face(
                    user["face_embedding"],
                    req.face_image,
                    FACE_SIMILARITY_THRESHOLD
                )
                face_verified = verified
                method = "password+face"
                
                if FACE_REQUIRED and not verified:
                    print(f"[ERROR] Face verification failed: {similarity} < {FACE_SIMILARITY_THRESHOLD}")
                    await db.log_login_event(str(user["user_id"]), False, method, client_ip)
                    raise HTTPException(
                        status_code=401, 
                        detail=f"Face verification failed (similarity: {similarity:.2f})"
                    )
            except Exception as e:
                print(f"[WARN] Face verification error: {e}")
                if FACE_REQUIRED:
                    raise HTTPException(status_code=401, detail="Face verification failed")
        
        # Create token
        token = auth_utils.create_access_token(
            str(user["user_id"]),
            user["username"],
            user["role"]
        )
        
        # Set httpOnly cookie
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False
        )
        
        # Log successful login
        await db.update_last_login(str(user["user_id"]))
        await db.log_login_event(str(user["user_id"]), True, method, client_ip)
        
        print(f"[OK] Login successful: {req.username}")
        return {
            "message": "Login successful",
            "user": {
                "user_id": str(user["user_id"]),
                "username": user["username"],
                "role": user["role"],
                "has_face": user.get("face_embedding") is not None
            },
            "face_verified": face_verified
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed internal error")


@app.post("/auth/logout")
async def logout(response: Response):
    """Clear auth cookie."""
    response.delete_cookie(key=COOKIE_NAME)
    return {"message": "Logged out successfully"}


@app.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse(
        user_id=str(user["user_id"]),
        username=user["username"],
        role=user["role"],
        has_face=user.get("face_embedding") is not None
    )


@app.post("/auth/face/enroll")
async def enroll_face(req: FaceEnrollRequest, user: dict = Depends(get_current_user)):
    """Enroll face for current user."""
    try:
        import face as face_utils
        
        embedding = face_utils.extract_embedding_from_base64(req.face_image)
        if embedding is None:
            raise HTTPException(status_code=400, detail="No face detected in image")
        
        success = await db.update_face_embedding(str(user["user_id"]), embedding)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save embedding")
        
        return {
            "message": "Face enrolled successfully",
            "embedding_size": len(embedding)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face enrollment failed: {str(e)}")


@app.post("/auth/face/verify")
async def verify_face(req: FaceVerifyRequest):
    """Verify face against stored embedding (for testing)."""
    user = await db.get_user_by_username(req.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get("face_embedding"):
        raise HTTPException(status_code=400, detail="User has no face enrolled")
    
    try:
        import face as face_utils
        
        verified, similarity = face_utils.verify_face(
            user["face_embedding"],
            req.face_image,
            FACE_SIMILARITY_THRESHOLD
        )
        
        return {
            "verified": verified,
            "similarity": round(similarity, 4),
            "threshold": FACE_SIMILARITY_THRESHOLD
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


# ============================================================
# LIFECYCLE
# ============================================================

@app.on_event("startup")
async def startup():
    """Initialize database pool on startup."""
    try:
        await db.get_pool()
        print("[OK] Connected to PostgreSQL")
    except Exception as e:
        print(f"[WARN] Database connection failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    """Close database pool on shutdown."""
    await db.close_pool()
    print("Database pool closed")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    from config import AUTH_PORT
    uvicorn.run(app, host="0.0.0.0", port=AUTH_PORT)
