import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class AgentScheduledJob(SQLModel, table=True):
	__tablename__ = "agent_scheduled_job"

	id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
	title: str = Field(nullable=False)
	instruction: str = Field(nullable=False)
	cron_expression: str = Field(nullable=False)
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
	)
