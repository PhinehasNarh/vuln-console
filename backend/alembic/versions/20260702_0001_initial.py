"""initial schemas and tables

Revision ID: 0001
Revises:
Create Date: 2026-07-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for schema in ("identity", "ingestion", "normalization"):
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="identity",
    )

    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("identity.users.id"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        schema="identity",
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.String(120), nullable=False),
        sa.Column("detail", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="identity",
    )
    op.create_index(
        "ix_identity_audit_events_actor", "audit_events", ["actor"], schema="identity"
    )
    op.create_index(
        "ix_identity_audit_events_action", "audit_events", ["action"], schema="identity"
    )
    op.create_index(
        "ix_identity_audit_events_created_at", "audit_events", ["created_at"], schema="identity"
    )

    op.create_table(
        "scans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("repository", sa.String(300), nullable=False),
        sa.Column("branch", sa.String(200), nullable=True),
        sa.Column("commit_sha", sa.String(64), nullable=True),
        sa.Column("format", sa.String(50), nullable=False),
        sa.Column("tool_name", sa.String(120), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("artifact_key", sa.String(500), nullable=False),
        sa.Column("artifact_size", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="ingestion",
    )
    op.create_index("ix_ingestion_scans_repository", "scans", ["repository"], schema="ingestion")
    op.create_index("ix_ingestion_scans_status", "scans", ["status"], schema="ingestion")
    op.create_index("ix_ingestion_scans_created_at", "scans", ["created_at"], schema="ingestion")

    op.create_table(
        "raw_findings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scan_id", sa.Uuid(), sa.ForeignKey("ingestion.scans.id"), nullable=False),
        sa.Column("finding_class", sa.String(20), nullable=False),
        sa.Column("rule_id", sa.String(300), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="ingestion",
    )
    op.create_index(
        "ix_ingestion_raw_findings_scan_id", "raw_findings", ["scan_id"], schema="ingestion"
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("finding_class", sa.String(20), nullable=False),
        sa.Column("rule_key", sa.String(400), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("repository", sa.String(300), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("tool_names", JSONB(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="normalization",
    )
    op.create_index(
        "ix_normalization_findings_fingerprint",
        "findings",
        ["fingerprint"],
        unique=True,
        schema="normalization",
    )
    for column in ("finding_class", "severity", "status", "repository", "first_seen"):
        op.create_index(
            f"ix_normalization_findings_{column}", "findings", [column], schema="normalization"
        )

    op.create_table(
        "finding_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "finding_id", sa.Uuid(), sa.ForeignKey("normalization.findings.id"), nullable=False
        ),
        sa.Column("raw_finding_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="normalization",
    )
    op.create_index(
        "ix_normalization_finding_sources_finding_id",
        "finding_sources",
        ["finding_id"],
        schema="normalization",
    )
    op.create_index(
        "ix_normalization_finding_sources_scan_id",
        "finding_sources",
        ["scan_id"],
        schema="normalization",
    )


def downgrade() -> None:
    op.drop_table("finding_sources", schema="normalization")
    op.drop_table("findings", schema="normalization")
    op.drop_table("raw_findings", schema="ingestion")
    op.drop_table("scans", schema="ingestion")
    op.drop_table("audit_events", schema="identity")
    op.drop_table("api_tokens", schema="identity")
    op.drop_table("users", schema="identity")
    for schema in ("normalization", "ingestion", "identity"):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}"')
