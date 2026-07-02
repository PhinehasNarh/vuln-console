"""fingerprint v2: correlation hints on raw findings, package/CVE on findings

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raw_findings",
        sa.Column("hints", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        schema="ingestion",
    )
    op.add_column(
        "findings", sa.Column("package", sa.String(300), nullable=True), schema="normalization"
    )
    op.add_column(
        "findings", sa.Column("cve_id", sa.String(40), nullable=True), schema="normalization"
    )
    op.add_column(
        "findings",
        sa.Column("fixed_version", sa.String(100), nullable=True),
        schema="normalization",
    )
    op.create_index(
        "ix_normalization_findings_cve_id", "findings", ["cve_id"], schema="normalization"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_normalization_findings_cve_id", table_name="findings", schema="normalization"
    )
    op.drop_column("findings", "fixed_version", schema="normalization")
    op.drop_column("findings", "cve_id", schema="normalization")
    op.drop_column("findings", "package", schema="normalization")
    op.drop_column("raw_findings", "hints", schema="ingestion")
