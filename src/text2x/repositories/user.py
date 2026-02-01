"""
Repository for User CRUD operations.

This module provides async database operations for the User model,
including authentication and user management operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from text2x.api.auth import verify_password, get_password_hash
from text2x.models.base import get_db
from text2x.models.user import User, UserRole


class UserRepository:
    """
    Repository for managing User entities.

    Provides async CRUD operations for users with authentication support.
    All methods that query by ID return None when the user is not found
    rather than raising exceptions.
    """

    async def create_user(
        self,
        email: str,
        password: str,
        name: str,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
    ) -> User:
        """
        Create a new user with hashed password.

        Args:
            email: User email address (must be unique)
            password: Plain text password (will be hashed)
            name: User's full name
            role: User role (default: USER)
            is_active: Whether the account is active (default: True)

        Returns:
            The newly created user

        Raises:
            IntegrityError: If email already exists
        """
        db = get_db()
        async with db.session() as session:
            hashed_password = get_password_hash(password)

            user = User(
                email=email,
                hashed_password=hashed_password,
                name=name,
                role=role,
                is_active=is_active,
            )

            session.add(user)
            await session.flush()
            await session.refresh(user)
            return user

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieve a user by ID.

        Args:
            user_id: The user UUID

        Returns:
            The user if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by email address.

        Args:
            email: The user email

        Returns:
            The user if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_users(
        self,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """
        List users with optional filters.

        Args:
            role: Filter by role (optional)
            is_active: Filter by active status (optional)

        Returns:
            List of users matching the filters, ordered by created_at desc
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(User).order_by(User.created_at.desc())

            # Apply filters
            if role is not None:
                stmt = stmt.where(User.role == role)
            if is_active is not None:
                stmt = stmt.where(User.is_active == is_active)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_user(
        self,
        user_id: UUID,
        email: Optional[str] = None,
        name: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[User]:
        """
        Update an existing user.

        Only provided fields will be updated. Password cannot be updated
        via this method (use update_password instead).

        Args:
            user_id: The user UUID
            email: New email (optional)
            name: New name (optional)
            role: New role (optional)
            is_active: New active status (optional)

        Returns:
            The updated user if found, None if user doesn't exist

        Raises:
            IntegrityError: If email conflicts with existing user
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                return None

            # Update only provided fields
            if email is not None:
                user.email = email
            if name is not None:
                user.name = name
            if role is not None:
                user.role = role
            if is_active is not None:
                user.is_active = is_active

            await session.flush()
            await session.refresh(user)
            return user

    async def update_password(
        self,
        user_id: UUID,
        new_password: str,
    ) -> Optional[User]:
        """
        Update a user's password.

        Args:
            user_id: The user UUID
            new_password: New plain text password (will be hashed)

        Returns:
            The updated user if found, None if user doesn't exist
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                return None

            user.hashed_password = get_password_hash(new_password)

            await session.flush()
            await session.refresh(user)
            return user

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete a user by ID.

        This performs a hard delete. Consider using deactivate_user
        instead for soft deletion.

        Args:
            user_id: The user UUID

        Returns:
            True if user was deleted, False if user was not found
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                return False

            await session.delete(user)
            return True

    async def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """
        Deactivate a user (soft delete).

        Args:
            user_id: The user UUID

        Returns:
            The deactivated user if found, None if user doesn't exist
        """
        return await self.update_user(user_id, is_active=False)

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            The user if authentication succeeds, None otherwise
        """
        user = await self.get_by_email(email)

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user
