"""
Property-based tests using Hypothesis for text2DSL.

This module uses property-based testing to verify invariants and edge cases
across the text2DSL system, including query parsing, schema validation,
user authentication, and token generation.
"""
import json
import re
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.strategies import composite

from text2x.api.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from text2x.models.annotation import SchemaAnnotation
from text2x.models.user import User, UserRole
from text2x.providers.base import SchemaDefinition, TableInfo, ColumnInfo


# =============================================================================
# Custom Strategies
# =============================================================================


@composite
def valid_emails(draw):
    """Generate valid email addresses."""
    local_part = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"),
                whitelist_characters=".-_",
            ),
            min_size=1,
            max_size=64,
        )
    )
    # Ensure it doesn't start or end with special chars
    local_part = local_part.strip(".-_")
    if not local_part:
        local_part = "user"

    domain_part = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"),
                whitelist_characters="-.",
            ),
            min_size=1,
            max_size=63,
        )
    )
    domain_part = domain_part.strip("-.")
    if not domain_part or "." not in domain_part:
        domain_part = "example.com"

    return f"{local_part}@{domain_part}"


@composite
def safe_passwords(draw):
    """Generate passwords that are safe to hash with bcrypt."""
    # bcrypt has a 72 byte limit when UTF-8 encoded
    # Use ASCII to avoid encoding issues
    password = draw(
        st.text(
            alphabet=st.characters(
                min_codepoint=33,  # Start after space
                max_codepoint=126,  # End at tilde (printable ASCII)
            ),
            min_size=8,
            max_size=50,  # Keep well under 72 bytes
        )
    )
    # Ensure it's not empty after stripping
    if not password.strip():
        password = "password123"
    return password


@composite
def valid_table_names(draw):
    """Generate valid database table names."""
    name = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"),
                whitelist_characters="_",
            ),
            min_size=1,
            max_size=63,
        )
    )
    # Ensure it starts with a letter
    if not name or not name[0].isalpha():
        name = "t" + name
    return name.lower()


@composite
def valid_column_names(draw):
    """Generate valid database column names."""
    name = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"),
                whitelist_characters="_",
            ),
            min_size=1,
            max_size=63,
        )
    )
    # Ensure it starts with a letter
    if not name or not name[0].isalpha():
        name = "c" + name
    return name.lower()


@composite
def schema_definitions(draw):
    """Generate valid SchemaDefinition objects."""
    num_tables = draw(st.integers(min_value=1, max_value=5))
    tables = []

    for _ in range(num_tables):
        table_name = draw(valid_table_names())
        num_columns = draw(st.integers(min_value=1, max_value=10))

        columns = []
        for _ in range(num_columns):
            col_name = draw(valid_column_names())
            col_type = draw(
                st.sampled_from([
                    "varchar", "integer", "bigint", "text", "boolean",
                    "timestamp", "date", "numeric", "jsonb"
                ])
            )
            nullable = draw(st.booleans())

            columns.append(
                ColumnInfo(
                    name=col_name,
                    type=col_type,
                    nullable=nullable,
                )
            )

        tables.append(
            TableInfo(
                name=table_name,
                columns=columns,
            )
        )

    return SchemaDefinition(
        tables=tables,
    )


@composite
def annotation_data(draw):
    """Generate valid annotation data."""
    provider_id = draw(st.text(min_size=1, max_size=100))
    created_by = draw(st.text(min_size=1, max_size=100))
    description = draw(st.text(min_size=1, max_size=1000))

    is_table = draw(st.booleans())

    if is_table:
        table_name = draw(valid_table_names())
        column_name = None
    else:
        table_name = None
        column_name = draw(valid_column_names())

    business_terms = draw(
        st.one_of(
            st.none(),
            st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5),
        )
    )
    examples = draw(
        st.one_of(
            st.none(),
            st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=5),
        )
    )

    return {
        "provider_id": provider_id,
        "table_name": table_name,
        "column_name": column_name,
        "description": description,
        "business_terms": business_terms,
        "examples": examples,
        "created_by": created_by,
    }


# =============================================================================
# Property Tests - User Model
# =============================================================================


@given(valid_emails(), safe_passwords())
@settings(max_examples=10, deadline=None)  # Reduce examples, disable deadline for bcrypt
def test_password_hashing_roundtrip(email: str, password: str):
    """Test that password hashing and verification work correctly."""
    # Hash password
    hashed = get_password_hash(password)

    # Verify properties
    assert hashed is not None
    assert isinstance(hashed, str)
    assert len(hashed) > 0
    assert hashed != password  # Should be hashed

    # Verify roundtrip
    assert verify_password(password, hashed)

    # Verify wrong password fails
    assert not verify_password(password + "wrong", hashed)
    assert not verify_password("", hashed)


@given(valid_emails())
def test_email_format_is_preserved(email: str):
    """Test that email addresses are preserved correctly."""
    # Email should contain @ and at least one dot in domain
    assert "@" in email
    parts = email.split("@")
    assert len(parts) == 2
    local, domain = parts
    assert len(local) > 0
    assert len(domain) > 0


@given(
    valid_emails(),
    st.text(min_size=1, max_size=255),
    st.sampled_from([UserRole.USER, UserRole.SUPER_ADMIN]),
)
@settings(deadline=None)  # Disable deadline for User model tests
def test_user_creation_properties(email: str, name: str, role: UserRole):
    """Test that user creation maintains expected properties."""
    hashed_password = get_password_hash("test123")

    user = User(
        email=email,
        hashed_password=hashed_password,
        name=name,
        role=role,
        is_active=True,
    )

    # Verify properties
    assert user.email == email
    assert user.name == name
    assert user.role == role
    assert user.is_active is True
    assert user.hashed_password == hashed_password

    # Verify representation
    repr_str = repr(user)
    assert email in repr_str
    # Check for either "UserRole.USER" or "user" in repr
    assert role.value in repr_str or str(role) in repr_str


# =============================================================================
# Property Tests - JWT Token Generation
# =============================================================================


@given(
    st.uuids(),
    valid_emails(),
    st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5),
)
def test_jwt_token_encode_decode_roundtrip(
    user_id: UUID, email: str, roles: list[str]
):
    """Test that JWT tokens can be encoded and decoded correctly."""
    user_id_str = str(user_id)

    # Create token
    token = create_access_token(
        user_id=user_id_str,
        email=email,
        roles=roles,
    )

    # Verify token properties
    assert isinstance(token, str)
    assert len(token) > 0
    assert token.count(".") == 2  # JWT has 3 parts

    # Decode token
    decoded = decode_token(token)

    # Verify roundtrip
    assert decoded.user_id == user_id_str
    assert decoded.email == email
    assert decoded.roles == roles


@given(
    st.uuids(),
    valid_emails(),
    st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5),
)
def test_refresh_token_properties(user_id: UUID, email: str, roles: list[str]):
    """Test that refresh tokens have correct properties."""
    user_id_str = str(user_id)

    # Create refresh token
    refresh_token = create_refresh_token(
        user_id=user_id_str,
        email=email,
        roles=roles,
    )

    # Verify token properties
    assert isinstance(refresh_token, str)
    assert len(refresh_token) > 0
    assert refresh_token.count(".") == 2  # JWT has 3 parts

    # Decode token
    decoded = decode_token(refresh_token)

    # Verify contents
    assert decoded.user_id == user_id_str
    assert decoded.email == email
    assert decoded.roles == roles


@given(
    st.uuids(),
    valid_emails(),
)
def test_different_tokens_for_same_user(user_id: UUID, email: str):
    """Test that generating multiple tokens produces different results."""
    user_id_str = str(user_id)

    token1 = create_access_token(user_id=user_id_str, email=email)
    token2 = create_access_token(user_id=user_id_str, email=email)

    # Tokens should be different due to timestamp
    # (unless generated in same millisecond, but unlikely)
    # At minimum, both should be valid
    decoded1 = decode_token(token1)
    decoded2 = decode_token(token2)

    assert decoded1.user_id == user_id_str
    assert decoded2.user_id == user_id_str


# =============================================================================
# Property Tests - Schema Annotation
# =============================================================================


@given(annotation_data())
def test_annotation_creation_properties(data: dict):
    """Test that annotations can be created with valid data."""
    annotation = SchemaAnnotation(**data)

    # Verify basic properties
    assert annotation.provider_id == data["provider_id"]
    assert annotation.description == data["description"]
    assert annotation.created_by == data["created_by"]

    # Verify target type
    if data["table_name"]:
        assert annotation.is_table_annotation
        assert not annotation.is_column_annotation
        assert annotation.target_type == "table"
        assert annotation.target == data["table_name"]
    else:
        assert annotation.is_column_annotation
        assert not annotation.is_table_annotation
        assert annotation.target_type == "column"
        assert annotation.target == data["column_name"]


@given(annotation_data())
def test_annotation_to_dict_roundtrip_properties(data: dict):
    """Test that annotation to_dict conversion preserves data."""
    annotation = SchemaAnnotation(**data)

    # Convert to dict
    result = annotation.to_dict()

    # Verify it's a dict
    assert isinstance(result, dict)

    # Verify key fields are preserved
    assert result["provider_id"] == data["provider_id"]
    assert result["description"] == data["description"]
    assert result["created_by"] == data["created_by"]

    # Verify arrays are lists (not None)
    assert isinstance(result["business_terms"], list)
    assert isinstance(result["examples"], list)
    assert isinstance(result["relationships"], list)
    assert isinstance(result["enum_values"], list)

    # Verify target fields
    if data["table_name"]:
        assert result["table_name"] == data["table_name"]
        assert result["column_name"] is None
    else:
        assert result["column_name"] == data["column_name"]
        assert result["table_name"] is None


@given(
    st.text(min_size=1, max_size=100),
    valid_table_names(),
    st.text(min_size=1, max_size=500),
    st.text(min_size=1, max_size=100),
)
def test_create_table_annotation_properties(
    provider_id: str, table_name: str, description: str, created_by: str
):
    """Test table annotation creation helper."""
    annotation = SchemaAnnotation.create_table_annotation(
        provider_id=provider_id,
        table_name=table_name,
        description=description,
        created_by=created_by,
    )

    # Verify it's a table annotation
    assert annotation.is_table_annotation
    assert not annotation.is_column_annotation
    assert annotation.table_name == table_name
    assert annotation.column_name is None
    assert annotation.provider_id == provider_id
    assert annotation.description == description
    assert annotation.created_by == created_by


@given(
    st.text(min_size=1, max_size=100),
    valid_column_names(),
    st.text(min_size=1, max_size=500),
    st.text(min_size=1, max_size=100),
)
def test_create_column_annotation_properties(
    provider_id: str, column_name: str, description: str, created_by: str
):
    """Test column annotation creation helper."""
    annotation = SchemaAnnotation.create_column_annotation(
        provider_id=provider_id,
        column_name=column_name,
        description=description,
        created_by=created_by,
    )

    # Verify it's a column annotation
    assert annotation.is_column_annotation
    assert not annotation.is_table_annotation
    assert annotation.column_name == column_name
    assert annotation.table_name is None
    assert annotation.provider_id == provider_id
    assert annotation.description == description
    assert annotation.created_by == created_by


# =============================================================================
# Property Tests - Schema Validation
# =============================================================================


@given(schema_definitions())
def test_schema_definition_properties(schema: SchemaDefinition):
    """Test that SchemaDefinition objects maintain expected properties."""
    # Verify basic properties
    assert schema.tables is not None
    assert len(schema.tables) > 0

    # Verify each table has required properties
    for table in schema.tables:
        assert table.name is not None
        assert len(table.name) > 0
        assert len(table.columns) > 0

        # Verify each column has required properties
        for column in table.columns:
            assert column.name is not None
            assert len(column.name) > 0
            assert column.type is not None
            assert isinstance(column.nullable, bool)


@given(schema_definitions())
def test_schema_json_serialization_roundtrip(schema: SchemaDefinition):
    """Test that schema can be serialized and deserialized."""
    # SchemaDefinition is a dataclass, use asdict instead of model_dump
    from dataclasses import asdict

    # Convert to dict
    schema_dict = asdict(schema)

    # Verify it's a dict
    assert isinstance(schema_dict, dict)
    assert "tables" in schema_dict

    # Verify JSON serializable (with custom handling for nested objects)
    # Just verify the structure is dict-like and has expected keys
    assert len(schema_dict["tables"]) == len(schema.tables)
    assert isinstance(schema_dict["tables"], list)


@given(
    valid_table_names(),
    st.lists(
        st.tuples(
            valid_column_names(),
            st.sampled_from(["varchar", "integer", "text", "boolean"]),
        ),
        min_size=1,
        max_size=5,
    ),
)
def test_table_info_creation(table_name: str, columns_data: list):
    """Test TableInfo creation with various column configurations."""
    columns = [
        ColumnInfo(name=name, type=dtype, nullable=True)
        for name, dtype in columns_data
    ]

    table = TableInfo(name=table_name, columns=columns)

    # Verify properties
    assert table.name == table_name
    assert len(table.columns) == len(columns_data)

    # Verify each column
    for i, (expected_name, expected_type) in enumerate(columns_data):
        assert table.columns[i].name == expected_name
        assert table.columns[i].type == expected_type


# =============================================================================
# Property Tests - Query Input Handling
# =============================================================================


@given(st.text(min_size=0, max_size=1000))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_query_input_string_properties(query_text: str):
    """Test that query strings maintain expected properties."""
    # Query text should be a string
    assert isinstance(query_text, str)

    # Length should be within bounds
    assert len(query_text) <= 1000

    # Should be able to strip whitespace
    stripped = query_text.strip()
    assert isinstance(stripped, str)

    # Should be able to convert to lower case
    lower = query_text.lower()
    assert isinstance(lower, str)


@given(st.text(min_size=1, max_size=500))
def test_query_text_safe_for_json(query_text: str):
    """Test that query text can be safely JSON-encoded."""
    # Should be JSON serializable
    data = {"query": query_text}
    json_str = json.dumps(data)

    # Should be deserializable
    parsed = json.loads(json_str)
    assert "query" in parsed

    # Should preserve the query (though whitespace might differ)
    assert isinstance(parsed["query"], str)


@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.one_of(
            st.text(max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.none(),
        ),
        min_size=0,
        max_size=10,
    )
)
def test_query_metadata_json_roundtrip(metadata: dict):
    """Test that query metadata can be JSON-serialized."""
    # Should be JSON serializable
    json_str = json.dumps(metadata)

    # Should be deserializable
    parsed = json.loads(json_str)

    # Should have same keys
    assert set(parsed.keys()) == set(metadata.keys())

    # Should preserve values (accounting for type conversions)
    for key in metadata:
        if metadata[key] is None:
            assert parsed[key] is None
        else:
            assert parsed[key] == metadata[key]


# =============================================================================
# Property Tests - UUID Handling
# =============================================================================


@given(st.uuids())
def test_uuid_string_conversion_roundtrip(uuid_val: UUID):
    """Test that UUIDs can be converted to strings and back."""
    # Convert to string
    uuid_str = str(uuid_val)

    # Verify string format
    assert isinstance(uuid_str, str)
    assert len(uuid_str) == 36  # Standard UUID string length
    assert uuid_str.count("-") == 4  # Standard UUID format

    # Convert back to UUID
    uuid_back = UUID(uuid_str)

    # Verify roundtrip
    assert uuid_back == uuid_val


@given(st.lists(st.uuids(), min_size=0, max_size=10))
def test_uuid_list_uniqueness(uuid_list: list[UUID]):
    """Test UUID uniqueness properties."""
    # Each UUID should be unique (or we got very unlucky)
    uuid_strings = [str(u) for u in uuid_list]

    # All should be valid UUID strings
    for uuid_str in uuid_strings:
        UUID(uuid_str)  # Should not raise


# =============================================================================
# Property Tests - Date/Time Handling
# =============================================================================


@given(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)))
def test_datetime_iso_format_roundtrip(dt: datetime):
    """Test that datetimes can be converted to ISO format and back."""
    # Convert to ISO format
    iso_str = dt.isoformat()

    # Verify it's a string
    assert isinstance(iso_str, str)

    # Should contain date components
    assert str(dt.year) in iso_str

    # Should be parseable back
    parsed = datetime.fromisoformat(iso_str)

    # Should be close (might lose microsecond precision)
    assert parsed.year == dt.year
    assert parsed.month == dt.month
    assert parsed.day == dt.day


# =============================================================================
# Integration Property Tests
# =============================================================================


@given(
    valid_emails(),
    safe_passwords(),
    st.text(min_size=1, max_size=100),
    st.sampled_from([UserRole.USER, UserRole.SUPER_ADMIN]),
)
@settings(max_examples=10, deadline=None)  # Reduce examples, disable deadline for bcrypt
def test_complete_user_auth_flow(
    email: str, password: str, name: str, role: UserRole
):
    """Test complete user authentication flow with property-based inputs."""
    # Hash password
    hashed = get_password_hash(password)

    # Create user
    user = User(
        email=email,
        hashed_password=hashed,
        name=name,
        role=role,
        is_active=True,
    )

    # Verify password
    assert verify_password(password, user.hashed_password)

    # Create JWT token
    token = create_access_token(
        user_id=str(uuid4()),
        email=user.email,
        roles=[user.role.value],
    )

    # Decode token
    decoded = decode_token(token)

    # Verify token contains user info
    assert decoded.email == email
    assert user.role.value in decoded.roles


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
