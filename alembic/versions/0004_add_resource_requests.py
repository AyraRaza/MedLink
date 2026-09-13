"""add resource requests

Revision ID: 0004_add_resource_requests
Revises: 0003_add_biomedical_resources
Create Date: 2026-09-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_add_resource_requests"
down_revision: Union[str, Sequence[str], None] = "0003_add_biomedical_resources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resource_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("requesting_organization_id", sa.Integer(), nullable=False),
        sa.Column("providing_organization_id", sa.Integer(), nullable=False),
        sa.Column("requesting_user_id", sa.Integer(), nullable=False),
        sa.Column("requested_quantity", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["resource_id"], ["biomedical_resources.id"],
            name="fk_resource_requests_resource_id_biomedical_resources",
        ),
        sa.ForeignKeyConstraint(
            ["requesting_organization_id"], ["organizations.id"],
            name="fk_resource_requests_requesting_organization_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["providing_organization_id"], ["organizations.id"],
            name="fk_resource_requests_providing_organization_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["requesting_user_id"], ["users.id"],
            name="fk_resource_requests_requesting_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resource_requests_resource_id", "resource_requests", ["resource_id"], unique=False
    )
    op.create_index(
        "ix_resource_requests_requesting_organization_id",
        "resource_requests",
        ["requesting_organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_resource_requests_providing_organization_id",
        "resource_requests",
        ["providing_organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_resource_requests_requesting_user_id",
        "resource_requests",
        ["requesting_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_resource_requests_status", "resource_requests", ["status"], unique=False
    )
    op.create_index(
        "ix_resource_requests_created_at", "resource_requests", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_resource_requests_created_at", table_name="resource_requests")
    op.drop_index("ix_resource_requests_status", table_name="resource_requests")
    op.drop_index("ix_resource_requests_requesting_user_id", table_name="resource_requests")
    op.drop_index(
        "ix_resource_requests_providing_organization_id", table_name="resource_requests"
    )
    op.drop_index(
        "ix_resource_requests_requesting_organization_id", table_name="resource_requests"
    )
    op.drop_index("ix_resource_requests_resource_id", table_name="resource_requests")
    op.drop_table("resource_requests")
