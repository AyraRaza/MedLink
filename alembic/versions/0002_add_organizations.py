"""add organizations and user org association

Revision ID: 0002_add_organizations
Revises: 0001_create_users
Create Date: 2026-08-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_organizations"
down_revision: Union[str, Sequence[str], None] = "0001_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("registration_number", sa.String(length=128), nullable=False),
        sa.Column(
            "organization_type",
            sa.String(length=32),
            server_default="HOSPITAL",
            nullable=False,
        ),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("pincode", sa.String(length=16), nullable=True),
        sa.Column(
            "verification_status",
            sa.String(length=32),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_number"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_organizations_name"), "organizations", ["name"], unique=False)
    op.create_index(
        op.f("ix_organizations_registration_number"),
        "organizations",
        ["registration_number"],
        unique=True,
    )
    op.create_index(op.f("ix_organizations_email"), "organizations", ["email"], unique=True)
    op.create_index(
        op.f("ix_organizations_verification_status"),
        "organizations",
        ["verification_status"],
        unique=False,
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            op.f("ix_users_organization_id"), ["organization_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_users_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_organization_id_organizations", type_="foreignkey")
        batch_op.drop_index(op.f("ix_users_organization_id"))
        batch_op.drop_column("organization_id")
    op.drop_index(op.f("ix_organizations_verification_status"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_email"), table_name="organizations")
    op.drop_index(
        op.f("ix_organizations_registration_number"), table_name="organizations"
    )
    op.drop_index(op.f("ix_organizations_name"), table_name="organizations")
    op.drop_table("organizations")
