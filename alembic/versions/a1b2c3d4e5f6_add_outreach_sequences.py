"""add outreach sequences and follow-up workflow tables

Revision ID: a1b2c3d4e5f6
Revises: 5f39c8072dde
Create Date: 2026-07-09 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "5f39c8072dde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("contact_email", sa.String(length=255), nullable=True))

    op.create_table(
        "outreach_sequences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_objective", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sequence_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sequence_id", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("delay_days", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("auto_send", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sequence_id"], ["outreach_sequences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sequence_steps_sequence_id"), "sequence_steps", ["sequence_id"], unique=False)

    op.create_table(
        "sequence_enrollments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("sequence_id", sa.Integer(), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sequence_id"], ["outreach_sequences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sequence_enrollments_company_id"), "sequence_enrollments", ["company_id"], unique=False)
    op.create_index(op.f("ix_sequence_enrollments_sequence_id"), "sequence_enrollments", ["sequence_id"], unique=False)

    op.create_table(
        "outreach_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.Integer(), nullable=True),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("cta", sa.String(length=255), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["sequence_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["sequence_steps.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outreach_messages_enrollment_id"), "outreach_messages", ["enrollment_id"], unique=False)

    op.create_table(
        "reply_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("in_reply_to", sa.String(length=255), nullable=True),
        sa.Column("raw_headers", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["sequence_enrollments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reply_events_enrollment_id"), "reply_events", ["enrollment_id"], unique=False)

    # Seed default 3-step sequence
    op.execute(
        sa.text(
            """
            INSERT INTO outreach_sequences (name, description, default_objective, is_active)
            VALUES (
                'Default GTM Outreach',
                'Standard 3-step cold outreach with value-add follow-up and break-up email',
                'Introduce our GTM automation platform and request a brief demo',
                true
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO sequence_steps (sequence_id, step_number, delay_days, channel, prompt_template, auto_send)
            VALUES
            (
                1, 1, 0, 'email',
                'Write the initial personalized cold outreach email. Reference a specific pain point or buying signal. Keep it under 150 words and include a low-friction CTA.',
                true
            ),
            (
                1, 2, 3, 'email',
                'Write a value-add follow-up email referencing pain points from the prior outreach. Share a relevant insight or resource. Keep it brief, helpful, and not pushy.',
                true
            ),
            (
                1, 3, 7, 'email',
                'Write a final soft break-up email with a clear, low-friction CTA. Acknowledge they may be busy and leave the door open. This is the last email in the sequence.',
                true
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reply_events_enrollment_id"), table_name="reply_events")
    op.drop_table("reply_events")
    op.drop_index(op.f("ix_outreach_messages_enrollment_id"), table_name="outreach_messages")
    op.drop_table("outreach_messages")
    op.drop_index(op.f("ix_sequence_enrollments_sequence_id"), table_name="sequence_enrollments")
    op.drop_index(op.f("ix_sequence_enrollments_company_id"), table_name="sequence_enrollments")
    op.drop_table("sequence_enrollments")
    op.drop_index(op.f("ix_sequence_steps_sequence_id"), table_name="sequence_steps")
    op.drop_table("sequence_steps")
    op.drop_table("outreach_sequences")
    op.drop_column("companies", "contact_email")
