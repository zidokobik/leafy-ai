import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class Users(SQLModel, table=True):
	user_id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
	email: str = Field(unique=True, index=True)
	password_hash: str
	first_name: str | None = None
	last_name: str | None = None
	created_at: datetime = Field(
		default_factory=datetime.utcnow,
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
	)
	updated_at: datetime | None = Field(
		default=None,
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True),
	)
	last_login_at: datetime | None = Field(
		default=None,
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True),
	)
