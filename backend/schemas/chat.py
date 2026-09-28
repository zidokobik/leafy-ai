import uuid
from datetime import datetime
from typing import Literal

import ai.ui.ai_sdk
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ChatRequest(BaseModel):
	"""AI SDK UI chat request; `id` identifies the persisted conversation."""

	id: uuid.UUID
	messages: list[ai.ui.ai_sdk.UIMessage]


class ChatConversationSummary(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

	id: uuid.UUID
	title: str
	source: Literal["chat", "schedule"]
	schedule_id: uuid.UUID | None = None
	created_at: datetime
	updated_at: datetime


class ChatConversationDetail(ChatConversationSummary):
	messages: list[ai.ui.ai_sdk.UIMessage]
