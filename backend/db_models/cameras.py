from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class Cameras(SQLModel, table=True):
	__tablename__ = "cameras"

	id: str = Field(primary_key=True)
	label: str = Field(nullable=False)
	image_url: str | None = None
	captured_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
