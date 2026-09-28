from uuid import UUID

import ai.ui.ai_sdk
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.chat import ChatConversationDetail, ChatConversationSummary, ChatRequest
from backend.services import chat_history
from backend.services.agent.agent import stream_chat_response

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_auth_user)])


@router.post("", description="Stream a chat agent response for the given AI SDK UI message history.")
async def chat(request: ChatRequest) -> StreamingResponse:

	# Convert the `UIMessage` to `Message`
	messages, approvals = ai.ui.ai_sdk.to_messages(request.messages)

	return StreamingResponse(
		stream_chat_response(messages, approvals, conversation_id=request.id),
		headers=ai.ui.ai_sdk.UI_MESSAGE_STREAM_HEADERS,
	)


@router.get(
	"/conversations",
	response_model=list[ChatConversationSummary],
	description="List stored conversations, most recently updated first.",
)
async def list_conversations(session: AsyncDatabaseSession) -> list[ChatConversationSummary]:
	return await chat_history.list_conversations(session)


@router.get(
	"/conversations/{conversation_id}",
	response_model=ChatConversationDetail,
	description="Read one conversation including its messages in AI SDK UI format.",
)
async def read_conversation(conversation_id: UUID, session: AsyncDatabaseSession) -> ChatConversationDetail:
	conversation = await chat_history.get_conversation(session, conversation_id)
	if conversation is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
	return ChatConversationDetail(
		id=conversation.id,
		title=conversation.title,
		source=conversation.source,
		schedule_id=conversation.schedule_id,
		created_at=conversation.created_at,
		updated_at=conversation.updated_at,
		messages=await chat_history.get_conversation_ui_messages(session, conversation_id),
	)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: UUID, session: AsyncDatabaseSession) -> None:
	if not await chat_history.delete_conversation(session, conversation_id):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
