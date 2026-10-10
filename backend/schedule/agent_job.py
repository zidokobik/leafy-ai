import logging
import uuid

import ai
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db_models.agent_scheduled_job import AgentScheduledJob
from backend.db_models.chat_history import SCHEDULE_SOURCE
from backend.dependencies.database_session import get_engine
from backend.services import chat_history
from backend.services.agent.agent import SYSTEM_PROMPT as FARM_SYSTEM_PROMPT
from backend.services.agent.agent import build_agent, get_provider
from backend.settings import get_settings

SYSTEM_PROMPT = """
You are running as a scheduled background agent.

This conversation was triggered automatically by a schedule, not by an interactive user message.

Your task is to:

* Follow the scheduled instruction provided for this run.
* Use available tools to achieve the scheduled task effectively.
* Do not ask the user follow-up questions unless the task cannot reasonably be completed without missing information.
* Never guess device identity, measurements or safe operating limits. If information is missing, report it and do not propose an operation.
* Avoid conversational filler.
* Return only the useful result of this scheduled execution.
* If there is nothing meaningful to report or no action is required, return a concise indication of that.
* Do not assume a human is actively present during this run.
* Treat this execution as a single independent run unless prior context or memory is explicitly provided.
* Use propose_scheduled_operation instead of the chat proposal tool. Schedule identity is bound by the server.
* Submit at most one proposal per device this run. Never retry failed proposals automatically.
* Every proposal requires human approval in Logs. Scheduling is not approval and does not execute hardware.
* Before raising an alert, call list_alerts and reuse the exact alert_key of any existing active alert for the same condition so repeated runs update it instead of stacking duplicates. Use update_alert to refine or re-grade an existing alert without recording a new occurrence. Resolve alerts whose condition has verifiably cleared.
* Use send_email when this run newly raised a critical condition (raise_alert returned created=true) or newly escalated one to critical, and when the scheduled instruction explicitly asks for an emailed report. Never re-email a condition on a routine re-raise; admins were already notified.
"""

logger = logging.getLogger(__name__)


async def execute_agent_scheduled_job(job: AgentScheduledJob):
	"""
	Execute the given agent scheduled job.
	"""

	settings = get_settings()

	provider = get_provider()
	agent = build_agent(allow_proposals=True, schedule_id=job.id)
	model = ai.Model(id=settings.AI_MODEL, provider=provider)

	messages = [
		ai.system_message(FARM_SYSTEM_PROMPT + "\n\n" + SYSTEM_PROMPT),
		ai.user_message(job.instruction),
	]

	logger.info("Scheduled agent run started: %s", job.id)
	try:
		async with agent.run(model, messages) as stream:
			async for _event in stream:
				pass
	except Exception:
		logger.exception("Scheduled agent run failed: %s; inspect Logs before retrying", job.id)
		raise

	try:
		async with AsyncSession(get_engine(), expire_on_commit=False) as session:
			conversation = await chat_history.save_conversation(
				session,
				uuid.uuid4(),
				stream.messages,
				title=job.title,
				source=SCHEDULE_SOURCE,
				schedule_id=job.id,
			)
		logger.info("Scheduled agent run stored as conversation %s", conversation.id)
	except Exception:
		logger.exception("Failed to persist conversation for scheduled run %s", job.id)
	logger.info("Scheduled agent run finished: %s; this does not indicate hardware execution", job.id)
