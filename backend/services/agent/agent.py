from collections.abc import AsyncIterator
from uuid import UUID

import ai
import ai.ui.ai_sdk

from backend.settings import get_settings

from .agent_tools import miscelaneous, proposals, sensors

with open("system_prompt.md") as f:
	SYSTEM_PROMPT = f.read().strip()


def get_provider() -> ai.Provider:
	settings = get_settings()
	return ai.get_provider("vercel", api_key=settings.AI_GATEWAY_API_KEY.get_secret_value())


def build_agent(*, allow_proposals: bool = False, schedule_id: UUID | None = None) -> ai.Agent:
	proposal_tool = (
		proposals.scheduled_proposal_tool(schedule_id)
		if schedule_id is not None
		else proposals.propose_device_operation
	)
	return ai.Agent(
		tools=[
			miscelaneous.get_unix_timestamp,
			sensors.get_sensor_history,
			*([proposals.get_operation_devices, proposal_tool] if allow_proposals else []),
		]
	)


async def stream_chat_response(
	messages: list[ai.messages.Message],
	approvals: list[ai.ui.ai_sdk.ApprovalResponse] | None = None,
) -> AsyncIterator[str]:
	"""Run the chat agent over the given UI messages, yielding AI SDK UI SSE chunks."""
	# See: https://ai-python.dev/docs/basics/ai-sdk-ui#tool-approvals
	if approvals is None:
		approvals = []

	messages.insert(0, ai.system_message(SYSTEM_PROMPT))

	settings = get_settings()

	provider = get_provider()
	model = ai.Model(id=settings.AI_MODEL, provider=provider)
	agent = build_agent(allow_proposals=True)

	async with agent.run(model, messages) as stream:
		ai.ui.ai_sdk.apply_approvals(approvals)
		async for chunk in ai.ui.ai_sdk.to_sse(stream):
			yield chunk
