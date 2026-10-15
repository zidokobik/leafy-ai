import logging
from collections.abc import AsyncIterator
from uuid import UUID

import ai
import ai.ui.ai_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database_session import get_engine
from backend.schemas.chat import AnswerDetail
from backend.services import chat_history
from backend.settings import get_settings

from .agent_tools import alerts, camera, devices, email, miscelaneous, sensors, harvest_readiness,plant_readiness, proposals,

with open("system_prompt.md") as f:
	SYSTEM_PROMPT = f.read().strip()

logger = logging.getLogger(__name__)


def get_provider() -> ai.Provider:
	settings = get_settings()
	return ai.get_provider("vercel", api_key=settings.AI_GATEWAY_API_KEY.get_secret_value())


def build_agent(*, schedule_id: UUID | None = None) -> ai.Agent:
	return ai.Agent(
		tools=[
			miscelaneous.get_unix_timestamp,
			sensors.get_sensor_history,
			plant_readiness.get_plant_readiness,
			harvest_readiness.get_harvest_readiness,
			camera.list_cameras,
			camera.get_camera_image,
			alerts.list_alerts,
			alerts.raise_alert_tool(schedule_id),
			alerts.update_alert_tool(schedule_id),
			alerts.resolve_alert,
			email.send_email_tool(schedule_id),
			devices.list_devices,
			devices.list_device_proposals,
			devices.propose_device_run_tool(schedule_id),
		]
	)


async def stream_chat_response(
	messages: list[ai.messages.Message],
	approvals: list[ai.ui.ai_sdk.ApprovalResponse] | None = None,
	conversation_id: UUID | None = None,
	detail: AnswerDetail = "simple",
) -> AsyncIterator[str]:
	"""Run the chat agent over the given UI messages, yielding AI SDK UI SSE chunks.

	When `conversation_id` is given, the full run history is persisted after the
	stream completes, creating the conversation on first use. `detail` picks the
	answer style described in the system prompt.
	"""
	# See: https://ai-python.dev/docs/basics/ai-sdk-ui#tool-approvals
	if approvals is None:
		approvals = []

	messages.insert(0, ai.system_message(f"{SYSTEM_PROMPT}\n\nAnswer style for this reply: {detail}."))

	settings = get_settings()

	provider = get_provider()
	model = ai.Model(id=settings.AI_MODEL, provider=provider)
	agent = build_agent()

	async with agent.run(model, messages) as stream:
		ai.ui.ai_sdk.apply_approvals(approvals)
		async for chunk in ai.ui.ai_sdk.to_sse(stream):
			yield chunk

	if conversation_id is not None:
		try:
			async with AsyncSession(get_engine(), expire_on_commit=False) as session:
				await chat_history.save_conversation(session, conversation_id, stream.messages)
		except Exception:
			# The response already streamed; losing history must not break the chat.
			logger.exception("Failed to persist conversation %s", conversation_id)
