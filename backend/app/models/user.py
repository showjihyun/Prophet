"""User model with RBAC roles.
SPEC: docs/spec/06_API_SPEC.md#authentication
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Valid role constants
ROLE_ADMIN = "admin"    # full access
ROLE_EDITOR = "editor"  # create/run simulations
ROLE_VIEWER = "viewer"  # read-only

ROLE_HIERARCHY = {ROLE_VIEWER: 0, ROLE_EDITOR: 1, ROLE_ADMIN: 2}


class User(Base):
    """Registered user with a role-based access level.

    Roles (ascending privilege):
        viewer  — read-only access to projects and simulations
        editor  — create/run simulations
        admin   — full access including user management

    SPEC: docs/spec/06_API_SPEC.md#authentication
    """

    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=ROLE_VIEWER)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


__all__ = ["User", "ROLE_ADMIN", "ROLE_EDITOR", "ROLE_VIEWER", "ROLE_HIERARCHY"]
