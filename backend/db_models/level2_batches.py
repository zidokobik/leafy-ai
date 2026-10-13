from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class Level2Batch(SQLModel, table=True):
	__tablename__ = "level2_batches"

	id: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger, sa.Identity(always=True), primary_key=True))
	# Farm local time, no timezone (same clock as the camera frames).
	moved_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=False), nullable=False, unique=True))
	harvested_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=False)))
	note: str = Field(default="", sa_column=sa.Column(sa.Text, nullable=False, server_default=""))
