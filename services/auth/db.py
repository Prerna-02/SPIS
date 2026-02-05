"""
SPIS Auth Service - Database Connection
"""
import asyncpg
from typing import Optional, Dict, Any, List
from config import DATABASE_URL, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            min_size=2,
            max_size=10
        )
    return _pool


async def close_pool():
    """Close connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# ============================================================
# AUTH_USERS CRUD
# ============================================================

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT user_id, username, password_hash, role, face_embedding, created_at, last_login_at "
        "FROM auth_users WHERE username = $1",
        username
    )
    if row:
        return dict(row)
    return None


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT user_id, username, role, face_embedding, created_at, last_login_at "
        "FROM auth_users WHERE user_id = $1::uuid",
        user_id
    )
    if row:
        return dict(row)
    return None


async def create_user(username: str, password_hash: str, role: str = "operator") -> Dict[str, Any]:
    """Create new user."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO auth_users (username, password_hash, role) "
        "VALUES ($1, $2, $3) "
        "RETURNING user_id, username, role, created_at",
        username, password_hash, role
    )
    return dict(row)


async def update_face_embedding(user_id: str, embedding: List[float]) -> bool:
    """Store face embedding for user."""
    pool = await get_pool()
    result = await pool.execute(
        "UPDATE auth_users SET face_embedding = $1 WHERE user_id = $2::uuid",
        embedding, user_id
    )
    return result == "UPDATE 1"


async def update_last_login(user_id: str):
    """Update last login timestamp."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE auth_users SET last_login_at = now() WHERE user_id = $1::uuid",
        user_id
    )


async def log_login_event(user_id: Optional[str], success: bool, method: str, ip: str):
    """Log login attempt."""
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO auth_login_events (user_id, success, method, ip) VALUES ($1::uuid, $2, $3, $4)",
        user_id, success, method, ip
    )
