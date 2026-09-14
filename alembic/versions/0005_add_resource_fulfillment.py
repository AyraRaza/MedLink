"""add resource fulfillment statuses

Revision ID: 0005_add_resource_fulfillment
Revises: 0004_add_resource_requests
Create Date: 2026-09-13

The request status column is a string without a database enum or check
constraint, so adding FULFILLED and RECEIVED requires no schema operation.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0005_add_resource_fulfillment"
down_revision: Union[str, Sequence[str], None] = "0004_add_resource_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
