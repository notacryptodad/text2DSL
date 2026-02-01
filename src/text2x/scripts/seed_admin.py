#!/usr/bin/env python3
"""
Seed script to create default super admin user.

This script creates a default super admin user for the system:
- Email: admin@text2dsl.com
- Password: Admin123!
- Role: super_admin

Run this script during system startup or deployment to ensure
the default admin exists.
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add src to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from text2x.models.base import DatabaseConfig, init_db
from text2x.models.user import UserRole
from text2x.repositories.user import UserRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_ADMIN = {
    "email": "admin@text2dsl.com",
    "password": "Admin123!",
    "name": "System Administrator",
    "role": UserRole.SUPER_ADMIN,
}


async def seed_admin():
    """Create default super admin if it doesn't exist."""
    from text2x.models.base import get_db

    try:
        # Initialize database
        config = DatabaseConfig.from_env()
        db = init_db(config)

        # Check if admin already exists first
        repo = UserRepository()
        existing_admin = await repo.get_by_email(DEFAULT_ADMIN["email"])

        if existing_admin:
            logger.info(f"✅ Default admin already exists: {DEFAULT_ADMIN['email']}")
            return

        # Create admin user with explicit transaction
        async with db.session() as session:
            from text2x.api.auth import get_password_hash
            from text2x.models.user import User

            hashed_password = get_password_hash(DEFAULT_ADMIN["password"])

            admin = User(
                email=DEFAULT_ADMIN["email"],
                hashed_password=hashed_password,
                name=DEFAULT_ADMIN["name"],
                role=DEFAULT_ADMIN["role"],
                is_active=True,
            )

            session.add(admin)
            await session.commit()
            await session.refresh(admin)

            logger.info(f"✅ Default admin created successfully!")
            logger.info(f"   Email: {admin.email}")
            logger.info(f"   Role: {admin.role}")
            logger.info(f"   ID: {admin.id}")

    except Exception as e:
        logger.error(f"❌ Failed to seed admin: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(seed_admin())
