"""add biomedical resources table

Revision ID: 0003_add_biomedical_resources
Revises: 0002_add_organizations
Create Date: 2026-08-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_biomedical_resources"
down_revision: Union[str, Sequence[str], None] = "0002_add_organizations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "biomedical_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="EQUIPMENT"),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column(
            "availability_status",
            sa.String(length=32),
            nullable=False,
            server_default="AVAILABLE",
        ),
        sa.Column(
            "condition",
            sa.String(length=32),
            nullable=False,
            server_default="NEW",
        ),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_biomedical_resources_organization_id"),
        "biomedical_resources",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_biomedical_resources_category"),
        "biomedical_resources",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_biomedical_resources_availability_status"),
        "biomedical_resources",
        ["availability_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_biomedical_resources_name"),
        "biomedical_resources",
        ["name"],
        unique=False,
    )

    with op.batch_alter_table("biomedical_resources") as batch_op:
        batch_op.create_foreign_key(
            "fk_biomedical_resources_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("biomedical_resources") as batch_op:
        batch_op.drop_constraint(
            "fk_biomedical_resources_organization_id_organizations",
            type_="foreignkey",
        )
    op.drop_index(op.f("ix_biomedical_resources_name"), table_name="biomedical_resources")
    op.drop_index(
        op.f("ix_biomedical_resources_availability_status"),
        table_name="biomedical_resources",
    )
    op.drop_index(op.f("ix_biomedical_resources_category"), table_name="biomedical_resources")
    op.drop_index(
        op.f("ix_biomedical_resources_organization_id"),
        table_name="biomedical_resources",
    )
    op.drop_table("biomedical_resources")
