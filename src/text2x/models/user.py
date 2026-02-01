"""
User models for internal authentication and authorization.

This module provides the user management layer:
- User: Internal user accounts with authentication
- UserRole: Enumeration of user roles (super_admin, user)
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, String, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class UserRole(str, Enum):
    """User role enumeration."""

    SUPER_ADMIN = "super_admin"
    USER = "user"


class User(Base, UUIDMixin, TimestampMixin):
    """
    Internal user account for authentication.

    Users can authenticate with email/password and receive JWT tokens
    for API access. Users have roles that determine their permissions.

    Attributes:
        id: Unique user identifier (UUID)
        email: User email address (unique, used for login)
        hashed_password: Bcrypt hashed password
        name: User's full name
        role: User role (super_admin or user)
        is_active: Whether the user account is active
        created_at: When the user account was created
        updated_at: When the user account was last modified
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.USER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role={self.role}, is_active={self.is_active})>"
