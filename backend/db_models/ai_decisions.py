import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class AIDecision(SQLModel, table=True):
	__tablename__ = "ai_decisions"
	__table_args__ = (
		sa.CheckConstraint("length(trim(summary)) > 0"),
		sa.CheckConstraint("length(trim(recommendation)) > 0"),
	)

	decision_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
	summary: str = Field(sa_type=sa.Text)
	recommendation: str = Field(sa_type=sa.Text)
	schedule_id: uuid.UUID | None = Field(default=None, foreign_key="agent_scheduled_job.id", ondelete="SET NULL")
