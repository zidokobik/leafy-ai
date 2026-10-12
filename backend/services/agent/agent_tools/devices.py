from uuid import UUID

import ai
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database_session import get_engine
from backend.schemas.proposals import ProposalRead
from backend.services import devices as device_service
from backend.services import proposals as proposal_service

# Reviewer identity is for the dashboard, not the model.
_HIDDEN_PROPOSAL_FIELDS = {"reviewed_by", "reviewer_email"}


def _dump(proposal: ProposalRead) -> dict:
	return proposal.model_dump(mode="json", by_alias=True, exclude=_HIDDEN_PROPOSAL_FIELDS)


@ai.tool
async def list_devices() -> dict:
	"""List the farm's switchable devices with their live on/off state and any open proposal.

	Each device is one outlet on a Kasa powerboard. You cannot switch devices directly:
	propose a timed run with propose_device_run and a person approves it. People can also
	switch devices by hand, so a device that is on without a running proposal was switched
	on by a person. isOn is null when the powerboard cannot be reached (stateError says
	why). openProposal is the device's pending or running proposal; a device can only have
	one at a time.
	"""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		devices = await device_service.list_devices(session)
		boards = {state.powerboard_id: state for state in await device_service.read_powerboard_states(session)}
		open_proposals = {
			proposal.device_id: proposal
			for proposal in await proposal_service.list_proposals(session, list(proposal_service.OPEN_STATUSES), 100)
		}

	result = []
	for device in devices:
		board = boards.get(device.powerboard_id)
		is_on, state_error = None, None
		if board is None or board.outlets is None:
			state_error = board.error if board else "Powerboard state unavailable."
		elif device.outlet_num > len(board.outlets):
			state_error = f"The powerboard has no outlet {device.outlet_num}."
		else:
			is_on = board.outlets[device.outlet_num - 1]
		proposal = open_proposals.get(device.id)
		result.append(
			{
				"id": str(device.id),
				"name": device.name,
				"deviceType": device.device_type,
				"isOn": is_on,
				"stateError": state_error,
				"openProposal": _dump(proposal) if proposal else None,
			}
		)
	return {"devices": result, "maxDurationSeconds": proposal_service.MAX_DURATION_SECONDS}


@ai.tool
async def list_device_proposals(limit: int = 10) -> dict:
	"""Recent device run proposals, newest first, with how each was reviewed and how its run ended.

	Check this before proposing so you do not repeat a run a person just rejected unless
	conditions have materially changed. status is pending, running, completed, stopped
	(switched off early by a person), rejected, expired (not reviewed in time) or failed
	(resultMessage says why).
	"""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		proposals = await proposal_service.list_proposals(session, limit=max(1, min(limit, 50)))
	return {"proposals": [_dump(proposal) for proposal in proposals]}


def propose_device_run_tool(schedule_id: UUID | None = None):
	"""Bind trusted scheduler provenance outside the model-visible arguments."""

	@ai.tool
	async def propose_device_run(device_id: UUID, duration_seconds: int, reason: str) -> dict:
		"""Propose switching a device on for duration_seconds; it switches off by itself afterwards.

		Nothing happens until a person approves the proposal on the dashboard (Overview or
		Logs page); an unreviewed proposal expires after 30 minutes. Use a device id from
		list_devices. duration_seconds is 1 to 86400 and should be the shortest run that
		does the job. reason is shown to the reviewer: cite the readings that justify the run
		and any uncertainty. Fails if the device already has a pending or running proposal.
		"""
		async with AsyncSession(get_engine(), expire_on_commit=False) as session:
			proposal = await proposal_service.propose_run(
				session, device_id, duration_seconds, reason, schedule_id=schedule_id
			)
		return _dump(proposal)

	return propose_device_run
