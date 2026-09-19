import ai.ui.ai_sdk
from pydantic import BaseModel


class ChatRequest(BaseModel):
	messages: list[ai.ui.ai_sdk.UIMessage]
