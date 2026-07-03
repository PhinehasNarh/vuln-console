"""SLA + ownership fields on findings; notifications table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "findings", sa.Column("owner", sa.String(120), nullable=True), schema="normalization"
    )
    op.add_column(
        "findings",
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        schema="normalization",
    )
    op.add_column(
        "findings",
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        schema="normalization",
    )
    op.add_column(
        "findings",
        sa.Column("sla_breach_notified_at", sa.DateTime(timezone=True), nullable=True),
        schema="normalization",
    )
    op.create_index(
        "ix_normalization_findings_owner", "findings", ["owner"], schema="normalization"
    )
    op.create_index(
        "ix_normalization_findings_sla_due_at", "findings", ["sla_due_at"], schema="normalization"
    )

    # Backfill SLA due dates for existing findings using the default policy
    # (critical 3d, high 7d, medium 30d, low 90d; info has none).
    op.execute(
        """
        UPDATE normalization.findings
        SET sla_due_at = first_seen + (
            CASE severity
                WHEN 'critical' THEN INTERVAL '3 days'
                WHEN 'high'     THEN INTERVAL '7 days'
                WHEN 'medium'   THEN INTERVAL '30 days'
                WHEN 'low'      THEN INTERVAL '90 days'
                ELSE NULL
            END
        )
        WHERE sla_due_at IS NULL
        """
    )

    op.execute('CREATE SCHEMA IF NOT EXISTS "notifications"')
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event", sa.String(80), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("target", sa.String(300), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="notifications",
    )
    op.create_index(
        "ix_notifications_notifications_event", "notifications", ["event"], schema="notifications"
    )
    op.create_index(
        "ix_notifications_notifications_channel",
        "notifications",
        ["channel"],
        schema="notifications",
    )
    op.create_index(
        "ix_notifications_notifications_finding_id",
        "notifications",
        ["finding_id"],
        schema="notifications",
    )
    op.create_index(
        "ix_notifications_notifications_created_at",
        "notifications",
        ["created_at"],
        schema="notifications",
    )


def downgrade() -> None:
    op.drop_table("notifications", schema="notifications")
    op.execute('DROP SCHEMA IF EXISTS "notifications"')
    op.drop_index(
        "ix_normalization_findings_sla_due_at", table_name="findings", schema="normalization"
    )
    op.drop_index("ix_normalization_findings_owner", table_name="findings", schema="normalization")
    op.drop_column("findings", "sla_breach_notified_at", schema="normalization")
    op.drop_column("findings", "sla_due_at", schema="normalization")
    op.drop_column("findings", "assigned_at", schema="normalization")
    op.drop_column("findings", "owner", schema="normalization")
