import ai.ui.ai_sdk
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.dependencies.auth import get_current_auth_user
from backend.schemas.chat import ChatRequest
from backend.services.agent.agent import stream_chat_response

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_auth_user)])


@router.post("", description="Stream a chat agent response for the given AI SDK UI message history.")
async def chat(request: ChatRequest) -> StreamingResponse:

	# Convert the `UIMessage` to `Message`
	messages, approvals = ai.ui.ai_sdk.to_messages(request.messages)

	return StreamingResponse(
		stream_chat_response(messages, approvals),
		headers=ai.ui.ai_sdk.UI_MESSAGE_STREAM_HEADERS,
	)
