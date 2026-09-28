import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

CHAT_SOURCE = "chat"
SCHEDULE_SOURCE = "schedule"


class ChatConversation(SQLModel, table=True):
	__tablename__ = "chat_conversations"
	__table_args__ = (
		sa.CheckConstraint("length(trim(title)) > 0"),
		sa.CheckConstraint("source IN ('chat', 'schedule')"),
	)

	id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
	title: str = Field(sa_type=sa.Text)
	source: str = Field(default=CHAT_SOURCE, sa_type=sa.Text)
	schedule_id: uuid.UUID | None = Field(default=None, foreign_key="agent_scheduled_job.id", ondelete="SET NULL")
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
	updated_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)


class ChatMessage(SQLModel, table=True):
	__tablename__ = "chat_messages"
	__table_args__ = (
		sa.CheckConstraint("seq >= 0"),
		sa.UniqueConstraint("conversation_id", "seq", name="chat_messages_conversation_seq_unique"),
	)

	id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
	conversation_id: uuid.UUID = Field(foreign_key="chat_conversations.id", ondelete="CASCADE")
	seq: int
	payload: dict[str, Any] = Field(sa_column=sa.Column(JSONB, nullable=False))
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),
		sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
