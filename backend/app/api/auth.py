"""Simple JWT authentication endpoints.
SPEC: docs/spec/06_API_SPEC.md
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# In-memory user store (no DB migration required for basic auth)
_users: dict[str, dict[str, Any]] = {}  # username -> {password_hash, user_id, created_at}

_JWT_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24


# ── Schemas ──────────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str


class RegisterResponse(BaseModel):
    user_id: str
    username: str


class LoginResponse(BaseModel):
    token: str
    user_id: str
    username: str


class MeResponse(BaseModel):
    user_id: str
    username: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _make_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def _decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: AuthRequest) -> RegisterResponse:
    """Register a new user. Returns user_id."""
    if body.username in _users:
        raise HTTPException(status_code=409, detail="Username already taken")
    user_id = str(uuid.uuid4())
    _users[body.username] = {
        "user_id": user_id,
        "password_hash": _hash_password(body.password),
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    return RegisterResponse(user_id=user_id, username=body.username)


@router.post("/login", response_model=LoginResponse)
async def login(body: AuthRequest) -> LoginResponse:
    """Verify credentials and return JWT token."""
    user = _users.get(body.username)
    if not user or user["password_hash"] != _hash_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = _make_token(user["user_id"], body.username)
    return LoginResponse(token=token, user_id=user["user_id"], username=body.username)


@router.get("/me", response_model=MeResponse)
async def me(authorization: str = Header(default="")) -> MeResponse:
    """Return current user from Bearer JWT token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[len("Bearer "):]
    payload = _decode_token(token)
    return MeResponse(user_id=payload["user_id"], username=payload["username"])
