"""Triage lifecycle: status disposition fields on findings

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "findings", sa.Column("status_reason", sa.Text(), nullable=True), schema="normalization"
    )
    op.add_column(
        "findings",
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
        schema="normalization",
    )
    op.add_column(
        "findings",
        sa.Column("status_changed_by", sa.String(120), nullable=True),
        schema="normalization",
    )
    op.add_column(
        "findings",
        sa.Column("risk_accepted_until", sa.DateTime(timezone=True), nullable=True),
        schema="normalization",
    )
    op.create_index(
        "ix_normalization_findings_risk_accepted_until",
        "findings",
        ["risk_accepted_until"],
        schema="normalization",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_normalization_findings_risk_accepted_until",
        table_name="findings",
        schema="normalization",
    )
    op.drop_column("findings", "risk_accepted_until", schema="normalization")
    op.drop_column("findings", "status_changed_by", schema="normalization")
    op.drop_column("findings", "status_changed_at", schema="normalization")
    op.drop_column("findings", "status_reason", schema="normalization")
