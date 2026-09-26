import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class Device(SQLModel, table=True):
	__tablename__ = "devices"

	device_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	device_name: str | None = None
	device_category: str | None = None
	device_type: str | None = None
	level_id: uuid.UUID | None = None
	measurement_unit: str | None = Field(default=None, sa_type=sa.Text)
	status: str | None = None
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
