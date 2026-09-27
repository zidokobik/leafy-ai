from uuid import UUID

import ai
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database_session import get_engine
from backend.services.agent_proposals import list_proposal_devices, propose_operation


@ai.tool
async def get_operation_devices(offset: int = 0) -> dict:
	"""Read real device IDs and configured duration limits. Follow nextOffset for more devices.

	A rule does not establish agronomic safety or prove that a device is online.
	"""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		return await list_proposal_devices(session, offset)


@ai.tool
async def propose_device_operation(device_id: UUID, duration_seconds: int, summary: str, recommendation: str) -> dict:
	"""Record an AI decision and submit a duration proposal for backend safety checks.

	Use only a real device UUID from get_operation_devices. Include evidence and
	uncertainty in summary, and the operation's reason in recommendation. Expires
	in ten minutes. Never approves or executes; report returned status and requestId.
	Do not retry automatically on error: a decision/request may already be stored.
	"""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		return await propose_operation(session, device_id, duration_seconds, summary, recommendation)


def scheduled_proposal_tool(schedule_id: UUID):
	"""Bind trusted scheduler context outside the model-visible arguments."""
	attempted_devices: set[UUID] = set()

	@ai.tool
	async def propose_scheduled_operation(
		device_id: UUID,
		duration_seconds: int,
		summary: str,
		recommendation: str,
	) -> dict:
		"""Submit one duration proposal per device this run, subject to safety checks.

		Use a real device UUID from get_operation_devices. Never approves or executes.
		Expires in ten minutes; human review is required in Logs. Do not retry errors.
		"""
		if device_id in attempted_devices:
			return {"error": "Already attempted a proposal for this device in this run. Check Logs; do not retry."}
		attempted_devices.add(device_id)
		async with AsyncSession(get_engine(), expire_on_commit=False) as session:
			return await propose_operation(
				session,
				device_id,
				duration_seconds,
				summary,
				recommendation,
				schedule_id=schedule_id,
			)

	return propose_scheduled_operation
