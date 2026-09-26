import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class CommandRequest(SQLModel, table=True):
	__tablename__ = "command_requests"
	__table_args__ = (
		sa.CheckConstraint("action_type IN ('run_for_duration')"),
		sa.CheckConstraint("duration_seconds > 0"),
		sa.CheckConstraint("length(trim(reason)) > 0"),
		sa.CheckConstraint(
			"status IN ('pending_approval', 'blocked', 'approved', 'rejected', 'expired', 'executing', 'succeeded', 'failed', 'unknown')"
		),
		sa.CheckConstraint("expires_at > created_at", name="command_requests_expiry_check"),
		sa.CheckConstraint(
			"finished_at IS NULL OR (started_at IS NOT NULL AND finished_at >= started_at)",
			name="command_requests_execution_time_check",
		),
	)

	request_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	decision_id: uuid.UUID | None = Field(default=None, foreign_key="ai_decisions.decision_id")
	device_id: uuid.UUID = Field(foreign_key="devices.device_id")
	action_type: str = Field(
		default="run_for_duration", sa_column=sa.Column(sa.Text, nullable=False, server_default="run_for_duration")
	)
	duration_seconds: int
	reason: str = Field(sa_type=sa.Text)
	status: str = Field(
		default="pending_approval", sa_column=sa.Column(sa.Text, nullable=False, server_default="pending_approval")
	)
	reviewed_by: uuid.UUID | None = Field(default=None, foreign_key="users.user_id", ondelete="SET NULL")
	reviewed_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
	expires_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
	started_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
	finished_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
	result_message: str | None = Field(default=None, sa_type=sa.Text)
