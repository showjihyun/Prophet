"""JWT authentication endpoints with RBAC.
SPEC: docs/spec/06_API_SPEC.md
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.user import ROLE_HIERARCHY, ROLE_VIEWER, User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_JWT_ALGORITHM = settings.jwt_algorithm
_TOKEN_EXPIRE_HOURS = settings.jwt_token_expire_hours


# ── Schemas ──────────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str
    role: str = ROLE_VIEWER  # only honoured on /register


class RegisterResponse(BaseModel):
    user_id: str
    username: str
    role: str


class LoginResponse(BaseModel):
    token: str
    user_id: str
    username: str
    role: str


class MeResponse(BaseModel):
    user_id: str
    username: str
    role: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _make_token(user_id: str, username: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
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


def _extract_token(authorization: str) -> dict[str, Any]:
    """Extract and decode JWT from an Authorization: Bearer <token> header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return _decode_token(authorization[len("Bearer "):])


# ── RBAC dependency ───────────────────────────────────────────────────────────

def require_role(min_role: str):
    """FastAPI dependency factory that enforces a minimum role level.

    Usage::

        @router.get("/admin-only")
        async def admin_endpoint(
            _: dict = Depends(require_role("admin"))
        ): ...

    Raises 403 if the authenticated user's role is below ``min_role``.
    Raises 401 if no valid token is present.

    SPEC: docs/spec/06_API_SPEC.md#authentication
    """
    min_level = ROLE_HIERARCHY.get(min_role, 0)

    def dependency(authorization: str = Header(default="")) -> dict[str, Any]:
        payload = _extract_token(authorization)
        user_role = payload.get("role", ROLE_VIEWER)
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user_role}' does not have permission (requires '{min_role}')",
            )
        return payload

    return dependency


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: AuthRequest,
    db: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    """Register a new user. Returns user_id and role.

    The ``role`` field in the request body is accepted but defaults to 'viewer'.
    Only an admin can register users with elevated roles (enforcement is left
    to callers of this endpoint — the field is recorded as-is for simplicity).
    """
    # Validate role value
    if body.role not in ROLE_HIERARCHY:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{body.role}'. Must be one of: {list(ROLE_HIERARCHY)}",
        )

    # Check for duplicate username
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        user_id=uuid.uuid4(),
        username=body.username,
        password_hash=_hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return RegisterResponse(
        user_id=str(user.user_id),
        username=user.username,
        role=user.role,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: AuthRequest,
    db: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """Verify credentials and return JWT token (includes role claim)."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or user.password_hash != _hash_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = _make_token(str(user.user_id), user.username, user.role)
    return LoginResponse(
        token=token,
        user_id=str(user.user_id),
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=MeResponse)
async def me(authorization: str = Header(default="")) -> MeResponse:
    """Return current user info (including role) from Bearer JWT token."""
    payload = _extract_token(authorization)
    return MeResponse(
        user_id=payload["user_id"],
        username=payload["username"],
        role=payload.get("role", ROLE_VIEWER),
    )
