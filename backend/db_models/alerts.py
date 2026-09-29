import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class Alert(SQLModel, table=True):
	__tablename__ = "alerts"
	__table_args__ = (
		# At most one active alert per alert_key; raise_alert upserts against this index.
		sa.Index("alerts_active_key_unique", "alert_key", unique=True, postgresql_where=sa.text("status = 'active'")),
	)

	alert_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	alert_key: str = Field(sa_type=sa.Text)
	severity: str = Field(sa_type=sa.Text)
	title: str = Field(sa_type=sa.Text)
	message: str = Field(sa_type=sa.Text)
	status: str = Field(default="active", sa_type=sa.Text)
	occurrences: int = Field(default=1)
	schedule_id: uuid.UUID | None = Field(default=None, foreign_key="agent_scheduled_job.id", ondelete="SET NULL")
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
	updated_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
	resolved_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
	resolved_by: str | None = Field(default=None, sa_type=sa.Text)
	dismissed_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
