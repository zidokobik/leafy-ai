import ai.ui.ai_sdk
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.dependencies.auth import get_current_auth_user
from backend.schemas.chat import ChatRequest
from backend.services.agent.agent import stream_chat_response

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_auth_user)])


@router.post("", description="Stream a chat agent response for the given AI SDK UI message history.")
async def chat(request: ChatRequest) -> StreamingResponse:
	return StreamingResponse(
		stream_chat_response(request.messages),
		headers=ai.ui.ai_sdk.UI_MESSAGE_STREAM_HEADERS,
	)
