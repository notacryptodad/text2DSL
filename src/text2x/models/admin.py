"""
Workspace admin models for Text2DSL.

This module defines the database models for workspace administration,
including admin roles, invitations, and access control.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class AdminRole(str, Enum):
    """Admin roles within a workspace."""

    OWNER = "owner"  # Full control, can manage admins
    ADMIN = "admin"  # Can manage workspace settings and connections
    MEMBER = "member"  # Read access to workspace


class WorkspaceAdmin(Base, UUIDMixin, TimestampMixin):
    """
    Represents an admin or member of a workspace.

    WorkspaceAdmin tracks user membership in workspaces, including their role,
    invitation status, and when they accepted the invitation.

    Attributes:
        id: Unique workspace admin identifier (UUID)
        workspace_id: Parent workspace UUID
        user_id: User identifier (external user system)
        role: User's role in the workspace (owner, admin, member)
        invited_by: User ID who sent the invitation
        invited_at: When the invitation was sent
        accepted_at: When the user accepted the invitation (None if pending)
        created_at: When the record was created
        updated_at: When the record was last modified
    """

    __tablename__ = "workspace_admins"

    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[AdminRole] = mapped_column(
        SQLEnum(AdminRole, native_enum=False),
        nullable=False,
        default=AdminRole.MEMBER,
    )
    invited_by: Mapped[str] = mapped_column(String(255), nullable=False)
    invited_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_admin_user"),
        Index("ix_workspace_admins_workspace_role", "workspace_id", "role"),
        Index("ix_workspace_admins_user", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<WorkspaceAdmin(id={self.id}, workspace_id={self.workspace_id}, "
            f"user_id='{self.user_id}', role={self.role.value})>"
        )

    @property
    def is_pending(self) -> bool:
        """Check if the invitation is pending acceptance."""
        return self.accepted_at is None

    @property
    def is_accepted(self) -> bool:
        """Check if the invitation has been accepted."""
        return self.accepted_at is not None

    def accept_invitation(self) -> None:
        """Mark the invitation as accepted."""
        if self.accepted_at is None:
            self.accepted_at = datetime.utcnow()

    def can_manage_admins(self) -> bool:
        """Check if this admin can manage other admins."""
        return self.role == AdminRole.OWNER

    def can_manage_workspace(self) -> bool:
        """Check if this admin can manage workspace settings."""
        return self.role in (AdminRole.OWNER, AdminRole.ADMIN)

    def to_dict(self) -> dict:
        """
        Convert admin record to dictionary.

        Returns:
            Dictionary representation suitable for API responses
        """
        return {
            "id": str(self.id),
            "workspace_id": str(self.workspace_id),
            "user_id": self.user_id,
            "role": self.role.value,
            "invited_by": self.invited_by,
            "invited_at": self.invited_at.isoformat() if self.invited_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "is_pending": self.is_pending,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
