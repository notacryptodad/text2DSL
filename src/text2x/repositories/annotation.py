"""
Repository for SchemaAnnotation CRUD operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from text2x.models.base import get_db
from text2x.models.annotation import SchemaAnnotation


class SchemaAnnotationRepository:
    """Repository for managing SchemaAnnotation entities."""

    async def create(
        self,
        provider_id: str,
        description: str,
        created_by: str,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        business_terms: Optional[List[str]] = None,
        examples: Optional[List[str]] = None,
        relationships: Optional[List[str]] = None,
        date_format: Optional[str] = None,
        enum_values: Optional[List[str]] = None,
        sensitive: bool = False,
    ) -> SchemaAnnotation:
        """
        Create a new schema annotation.

        Args:
            provider_id: The provider ID this annotation belongs to
            description: Description of the table or column
            created_by: User who created the annotation
            table_name: Table name (for table-level annotations)
            column_name: Column name in format "table.column" (for column annotations)
            business_terms: Alternative names users might use
            examples: Example values or use cases
            relationships: Related tables or concepts
            date_format: Date/time format if applicable
            enum_values: Enumeration values if applicable
            sensitive: Whether the data is sensitive (PII)

        Returns:
            The newly created SchemaAnnotation
        """
        db = get_db()
        async with db.session() as session:
            annotation = SchemaAnnotation(
                provider_id=provider_id,
                table_name=table_name,
                column_name=column_name,
                description=description,
                created_by=created_by,
                business_terms=business_terms,
                examples=examples,
                relationships=relationships,
                date_format=date_format,
                enum_values=enum_values,
                sensitive=sensitive,
            )
            session.add(annotation)
            await session.flush()
            await session.commit()
            await session.refresh(annotation)
            return annotation

    async def get_by_id(self, annotation_id: UUID) -> Optional[SchemaAnnotation]:
        """
        Get an annotation by ID.

        Args:
            annotation_id: The annotation UUID

        Returns:
            The annotation if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(SchemaAnnotation).where(SchemaAnnotation.id == annotation_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_provider(self, provider_id: str) -> List[SchemaAnnotation]:
        """
        List all annotations for a provider.

        Args:
            provider_id: The provider ID

        Returns:
            List of annotations for the provider
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(SchemaAnnotation)
                .where(SchemaAnnotation.provider_id == provider_id)
                .order_by(SchemaAnnotation.table_name, SchemaAnnotation.column_name)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_table(
        self, provider_id: str, table_name: str
    ) -> List[SchemaAnnotation]:
        """
        List annotations for a specific table (including column annotations).

        Args:
            provider_id: The provider ID
            table_name: The table name

        Returns:
            List of annotations for the table
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(SchemaAnnotation)
                .where(
                    SchemaAnnotation.provider_id == provider_id,
                    (SchemaAnnotation.table_name == table_name) |
                    (SchemaAnnotation.column_name.like(f"{table_name}.%"))
                )
                .order_by(SchemaAnnotation.column_name)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_column(
        self, provider_id: str, column_name: str
    ) -> List[SchemaAnnotation]:
        """
        List annotations for a specific column.

        Args:
            provider_id: The provider ID
            column_name: The column name (format: "table.column")

        Returns:
            List of annotations for the column
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(SchemaAnnotation)
                .where(
                    SchemaAnnotation.provider_id == provider_id,
                    SchemaAnnotation.column_name == column_name
                )
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(
        self,
        annotation_id: UUID,
        description: Optional[str] = None,
        business_terms: Optional[List[str]] = None,
        examples: Optional[List[str]] = None,
        relationships: Optional[List[str]] = None,
        date_format: Optional[str] = None,
        enum_values: Optional[List[str]] = None,
        sensitive: Optional[bool] = None,
    ) -> Optional[SchemaAnnotation]:
        """
        Update an existing annotation.

        Args:
            annotation_id: The annotation UUID
            description: New description
            business_terms: New business terms
            examples: New examples
            relationships: New relationships
            date_format: New date format
            enum_values: New enum values
            sensitive: New sensitive flag

        Returns:
            The updated annotation if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(SchemaAnnotation).where(SchemaAnnotation.id == annotation_id)
            result = await session.execute(stmt)
            annotation = result.scalar_one_or_none()

            if annotation is None:
                return None

            if description is not None:
                annotation.description = description
            if business_terms is not None:
                annotation.business_terms = business_terms
            if examples is not None:
                annotation.examples = examples
            if relationships is not None:
                annotation.relationships = relationships
            if date_format is not None:
                annotation.date_format = date_format
            if enum_values is not None:
                annotation.enum_values = enum_values
            if sensitive is not None:
                annotation.sensitive = sensitive

            await session.flush()
            await session.commit()
            await session.refresh(annotation)
            return annotation

    async def delete(self, annotation_id: UUID) -> bool:
        """
        Delete an annotation.

        Args:
            annotation_id: The annotation UUID

        Returns:
            True if deleted, False if not found
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(SchemaAnnotation).where(SchemaAnnotation.id == annotation_id)
            result = await session.execute(stmt)
            annotation = result.scalar_one_or_none()

            if annotation is None:
                return False

            await session.delete(annotation)
            return True
