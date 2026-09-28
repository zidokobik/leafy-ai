import uuid
from datetime import UTC, datetime

import ai
import ai.ui.ai_sdk
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.chat_history import CHAT_SOURCE, ChatConversation, ChatMessage

MAX_TITLE_LENGTH = 80
DEFAULT_TITLE = "New conversation"


def derive_title(messages: list[ai.messages.Message]) -> str:
	"""Build a conversation title from the first non-empty user text part."""
	for message in messages:
		if message.role != "user":
			continue
		for part in message.parts:
			if isinstance(part, ai.messages.TextPart) and part.text.strip():
				text = " ".join(part.text.split())
				return text if len(text) <= MAX_TITLE_LENGTH else text[: MAX_TITLE_LENGTH - 1] + "…"
	return DEFAULT_TITLE


async def list_conversations(session: AsyncSession) -> list[ChatConversation]:
	query = select(ChatConversation).order_by(sa.desc(ChatConversation.updated_at))
	result = await session.execute(query)
	return result.scalars().all()


async def get_conversation(session: AsyncSession, conversation_id: uuid.UUID) -> ChatConversation | None:
	return await session.get(ChatConversation, conversation_id)


async def get_conversation_ui_messages(
	session: AsyncSession, conversation_id: uuid.UUID
) -> list[ai.ui.ai_sdk.UIMessage]:
	"""Load a conversation's stored runtime messages as AI SDK UI messages."""
	query = select(ChatMessage).where(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.seq)
	result = await session.execute(query)
	messages = [ai.messages.Message.model_validate(row.payload) for row in result.scalars()]
	return ai.ui.ai_sdk.to_ui_messages(messages)


async def save_conversation(
	session: AsyncSession,
	conversation_id: uuid.UUID,
	messages: list[ai.messages.Message],
	*,
	title: str | None = None,
	source: str = CHAT_SOURCE,
	schedule_id: uuid.UUID | None = None,
) -> ChatConversation:
	"""Create or update a conversation, replacing its stored messages wholesale.

	System messages are server-owned prompts and are never persisted. `title`,
	`source` and `schedule_id` only apply when the conversation does not exist yet.
	"""
	storable = [message for message in messages if message.role != "system"]

	conversation = await session.get(ChatConversation, conversation_id)
	if conversation is None:
		conversation = ChatConversation(
			id=conversation_id,
			title=title or derive_title(storable),
			source=source,
			schedule_id=schedule_id,
		)
		session.add(conversation)
	else:
		conversation.updated_at = datetime.now(UTC)

	await session.execute(sa.delete(ChatMessage).where(ChatMessage.conversation_id == conversation_id))
	for seq, message in enumerate(storable):
		session.add(
			ChatMessage(
				conversation_id=conversation_id,
				seq=seq,
				payload=message.model_dump(mode="json"),
			)
		)
	await session.commit()
	return conversation


async def delete_conversation(session: AsyncSession, conversation_id: uuid.UUID) -> bool:
	"""Delete a conversation; its messages cascade in the database."""
	conversation = await session.get(ChatConversation, conversation_id)
	if conversation is None:
		return False
	await session.delete(conversation)
	await session.commit()
	return True
