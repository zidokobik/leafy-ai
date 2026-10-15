import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

# Imported so the foreign keys below resolve whenever this model is used on its own.
from backend.db_models.agent_scheduled_job import AgentScheduledJob  # noqa: F401
from backend.db_models.devices import Device  # noqa: F401
from backend.db_models.users import Users  # noqa: F401


class DeviceProposal(SQLModel, table=True):
	"""An agent's proposal to run a device for a set time, plus its review and run outcome.

	powerboard_host and outlet_num snapshot the outlet that was switched on, so the
	automatic switch-off targets the same outlet even if the device is edited or deleted.
	"""

	__tablename__ = "device_proposals"
	__table_args__ = (
		sa.Index(
			"device_proposals_open_device_unique",
			"device_id",
			unique=True,
			postgresql_where=sa.text("status IN ('pending', 'running')"),
		),
	)

	id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	device_id: uuid.UUID | None = Field(default=None, foreign_key="devices.id", ondelete="SET NULL")
	device_name: str = Field(sa_type=sa.Text)
	duration_seconds: int
	reason: str = Field(sa_type=sa.Text)
	status: str = Field(default="pending", sa_type=sa.Text)
	schedule_id: uuid.UUID | None = Field(default=None, foreign_key="agent_scheduled_job.id", ondelete="SET NULL")
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
	expires_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
	reviewed_by: uuid.UUID | None = Field(default=None, foreign_key="users.user_id", ondelete="SET NULL")
	reviewed_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
	powerboard_host: str | None = Field(default=None, sa_type=sa.Text)
	outlet_num: int | None = None
	started_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
	ends_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
	finished_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
	result_message: str | None = Field(default=None, sa_type=sa.Text)
