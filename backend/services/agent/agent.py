from collections.abc import AsyncIterator

import ai
import ai.ui.ai_sdk

from backend.settings import get_settings

from . import tools

with open("system_prompt.md") as f:
	SYSTEM_PROMPT = f.read().strip()


def _build_agent() -> ai.Agent:
	return ai.Agent(tools=[tools.get_water_pH])


async def stream_chat_response(ui_messages: list[ai.ui.ai_sdk.UIMessage]) -> AsyncIterator[str]:
	"""Run the chat agent over the given UI messages, yielding AI SDK UI SSE chunks."""
	messages, approvals = ai.ui.ai_sdk.to_messages(ui_messages)
	messages.insert(0, ai.system_message(SYSTEM_PROMPT))

	settings = get_settings()

	provider = ai.get_provider("vercel", api_key=settings.AI_GATEWAY_API_KEY.get_secret_value())
	model = ai.Model(id=settings.AI_MODEL, provider=provider)
	agent = _build_agent()

	async with agent.run(model, messages) as stream:
		ai.ui.ai_sdk.apply_approvals(approvals)
		async for chunk in ai.ui.ai_sdk.to_sse(stream):
			yield chunk
