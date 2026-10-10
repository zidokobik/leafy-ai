import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel


class EmailRecipient(SQLModel, table=True):
	__tablename__ = "email_recipients"

	recipient_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	email: str = Field(sa_type=sa.Text, unique=True)
	label: str | None = Field(default=None, sa_type=sa.Text)
	enabled: bool = Field(default=True)
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)


class EmailLog(SQLModel, table=True):
	__tablename__ = "email_logs"

	email_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	recipients: list[str] = Field(sa_column=sa.Column(ARRAY(sa.Text()), nullable=False))
	subject: str = Field(sa_type=sa.Text)
	status: str = Field(sa_type=sa.Text)
	error: str | None = Field(default=None, sa_type=sa.Text)
	schedule_id: uuid.UUID | None = Field(default=None, foreign_key="agent_scheduled_job.id", ondelete="SET NULL")
	triggered_by: str = Field(sa_type=sa.Text)
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
