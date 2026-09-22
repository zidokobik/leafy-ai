import ai

from backend.db_models.agent_scheduled_job import AgentScheduledJob
from backend.services.agent.agent import build_agent, get_provider
from backend.settings import get_settings

SYSTEM_PROMPT = """
You are running as a scheduled background agent.

This conversation was triggered automatically by a schedule, not by an interactive user message.

Your task is to:

* Follow the scheduled instruction provided for this run.
* Use available tools when necessary.
* Do not ask the user follow-up questions unless the task cannot reasonably be completed without missing information.
* Make reasonable assumptions when needed and state them briefly.
* Avoid conversational filler.
* Return only the useful result of this scheduled execution.
* If there is nothing meaningful to report or no action is required, return a concise indication of that.
* Do not assume a human is actively present during this run.
* Treat this execution as a single independent run unless prior context or memory is explicitly provided.
"""


async def execute_agent_scheduled_job(job: AgentScheduledJob):
	"""
	Execute the given agent scheduled job.
	"""

	settings = get_settings()

	provider = get_provider()
	agent = build_agent()
	model = ai.Model(id=settings.AI_MODEL, provider=provider)

	messages = [
		ai.system_message(SYSTEM_PROMPT),
		ai.user_message(job.instruction),
	]

	async with agent.run(model, messages) as stream:
		async for chunk in ai.ui.ai_sdk.to_sse(stream):
			pass
