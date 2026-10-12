"""Device runs: the agent proposes a timed run, a person approves it, the outlet runs for the set time.

Approving switches the outlet on and arms an in-process timer that switches it off again
when the run ends. Timers are re-armed on startup, so a run that ended while the API was
down is switched off as soon as it is back. People can also switch a device by hand
(switch_device); switching off a device mid-run stops that run.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.device_proposals import DeviceProposal
from backend.db_models.devices import Device, Powerboard
from backend.db_models.users import Users
from backend.dependencies.database_session import get_engine
from backend.schemas.proposals import ProposalRead, ProposalStatus
from backend.services import alerts, outlets
from backend.services.devices import DeviceNotFoundError

logger = logging.getLogger(__name__)

PROPOSAL_TTL = timedelta(minutes=30)
MAX_DURATION_SECONDS = 24 * 60 * 60
MAX_REASON_LENGTH = 2000
AUTO_OFF_ATTEMPTS = 5
AUTO_OFF_RETRY_SECONDS = 30
OPEN_STATUSES: tuple[ProposalStatus, ...] = ("pending", "running")

_auto_off_tasks: dict[UUID, asyncio.Task] = {}


class ProposalNotFoundError(LookupError):
	pass


class ProposalConflictError(ValueError):
	"""The proposal is not in a state that allows the requested action."""


def _now() -> datetime:
	return datetime.now(UTC)


def _to_read(proposal: DeviceProposal, reviewer_email: str | None) -> ProposalRead:
	return ProposalRead.model_validate(proposal).model_copy(update={"reviewer_email": reviewer_email})


def _with_reviewer_email():
	return select(DeviceProposal, Users.email).outerjoin(Users, Users.user_id == DeviceProposal.reviewed_by)


async def _expire_stale(session: AsyncSession) -> None:
	await session.execute(
		sa.update(DeviceProposal)
		.where(DeviceProposal.status == "pending", DeviceProposal.expires_at <= sa.func.now())
		.values(status="expired", result_message="Not reviewed before it expired.")
		.execution_options(synchronize_session=False)
	)
	await session.commit()


async def _get_for_update(session: AsyncSession, proposal_id: UUID) -> DeviceProposal:
	proposal = (
		await session.execute(
			select(DeviceProposal)
			.where(DeviceProposal.id == proposal_id)
			.with_for_update()
			.execution_options(populate_existing=True)
		)
	).scalar_one_or_none()
	if proposal is None:
		raise ProposalNotFoundError("Proposal not found.")
	return proposal


async def get_proposal(session: AsyncSession, proposal_id: UUID) -> ProposalRead:
	row = (
		await session.execute(
			_with_reviewer_email().where(DeviceProposal.id == proposal_id).execution_options(populate_existing=True)
		)
	).one_or_none()
	if row is None:
		raise ProposalNotFoundError("Proposal not found.")
	return _to_read(*row)


async def list_proposals(
	session: AsyncSession, statuses: list[ProposalStatus] | None = None, limit: int = 50, offset: int = 0
) -> list[ProposalRead]:
	"""Proposals newest first, optionally filtered to the given statuses."""
	await _expire_stale(session)
	statement = _with_reviewer_email().order_by(DeviceProposal.created_at.desc()).limit(limit).offset(offset)
	if statuses:
		statement = statement.where(DeviceProposal.status.in_(statuses))
	return [_to_read(proposal, email) for proposal, email in (await session.execute(statement)).all()]


async def propose_run(
	session: AsyncSession,
	device_id: UUID,
	duration_seconds: int,
	reason: str,
	*,
	schedule_id: UUID | None = None,
) -> ProposalRead:
	"""Record a pending proposal to switch a device on for `duration_seconds`. Nothing is switched yet."""
	if not 1 <= duration_seconds <= MAX_DURATION_SECONDS:
		raise ValueError(f"duration_seconds must be between 1 and {MAX_DURATION_SECONDS} (24 hours).")
	reason = reason.strip()
	if not 0 < len(reason) <= MAX_REASON_LENGTH:
		raise ValueError(f"reason must be non-blank and at most {MAX_REASON_LENGTH} characters.")
	device = await session.get(Device, device_id)
	if device is None:
		raise DeviceNotFoundError("Device not found; use a device id from list_devices.")
	device_name = device.name

	await _expire_stale(session)
	open_proposal = (
		await session.execute(
			select(DeviceProposal).where(
				DeviceProposal.device_id == device_id, DeviceProposal.status.in_(OPEN_STATUSES)
			)
		)
	).scalar_one_or_none()
	if open_proposal is not None:
		raise ProposalConflictError(
			f"{device_name} already has a {open_proposal.status} proposal ({open_proposal.id}); "
			"wait until it is reviewed or its run ends."
		)

	now = _now()
	proposal = DeviceProposal(
		device_id=device_id,
		device_name=device_name,
		duration_seconds=duration_seconds,
		reason=reason,
		schedule_id=schedule_id,
		created_at=now,
		expires_at=now + PROPOSAL_TTL,
	)
	session.add(proposal)
	try:
		await session.commit()
	except IntegrityError as error:
		await session.rollback()
		raise ProposalConflictError(f"{device_name} already has a pending or running proposal.") from error
	return _to_read(proposal, None)


async def approve(session: AsyncSession, proposal_id: UUID, reviewer_id: UUID) -> ProposalRead:
	"""Approve a pending proposal and switch its outlet on now.

	A powerboard failure does not raise: the proposal is stored as failed with the reason.
	"""
	await _expire_stale(session)
	proposal = await _get_for_update(session, proposal_id)
	if proposal.status != "pending":
		raise ProposalConflictError(f"This proposal is already {proposal.status}.")
	proposal.reviewed_by = reviewer_id
	proposal.reviewed_at = _now()

	target = None
	if proposal.device_id is not None:
		target = (
			await session.execute(
				select(Powerboard.host, Device.outlet_num)
				.join(Powerboard, Powerboard.id == Device.powerboard_id)
				.where(Device.id == proposal.device_id)
			)
		).one_or_none()
	if target is None:
		proposal.status = "failed"
		proposal.result_message = "The device no longer exists."
	else:
		host, outlet_num = target
		# Timed from before connecting: switching off takes about as long, so the outlet is on for the duration.
		started_at = _now()
		try:
			await outlets.set_outlet(host, outlet_num, on=True)
		except outlets.PowerboardError as error:
			proposal.status = "failed"
			proposal.result_message = f"Could not switch on: {error}"
		else:
			proposal.status = "running"
			proposal.powerboard_host = host
			proposal.outlet_num = outlet_num
			proposal.started_at = started_at
			proposal.ends_at = started_at + timedelta(seconds=proposal.duration_seconds)

	ends_at = proposal.ends_at if proposal.status == "running" else None
	session.add(proposal)
	try:
		await session.commit()
	except Exception:
		await session.rollback()
		if ends_at is not None and target is not None:
			# Never leave an outlet on without a stored run that will switch it off.
			await _switch_off_quietly(*target)
		raise
	if ends_at is not None:
		_schedule_auto_off(proposal_id, ends_at)
	return await get_proposal(session, proposal_id)


async def reject(session: AsyncSession, proposal_id: UUID, reviewer_id: UUID) -> ProposalRead:
	await _expire_stale(session)
	proposal = await _get_for_update(session, proposal_id)
	if proposal.status != "pending":
		raise ProposalConflictError(f"This proposal is already {proposal.status}.")
	proposal.status = "rejected"
	proposal.reviewed_by = reviewer_id
	proposal.reviewed_at = _now()
	session.add(proposal)
	await session.commit()
	return await get_proposal(session, proposal_id)


async def stop(session: AsyncSession, proposal_id: UUID, user_id: UUID) -> ProposalRead:
	"""Switch a running device off before its run ends.

	Raises PowerboardError when the outlet cannot be switched off; the run stays running
	and its automatic switch-off still fires at the scheduled end.
	"""
	proposal = await _get_for_update(session, proposal_id)
	if proposal.status != "running":
		raise ProposalConflictError(f"Only running proposals can be stopped; this one is {proposal.status}.")
	try:
		await outlets.set_outlet(proposal.powerboard_host, proposal.outlet_num, on=False)
	except outlets.PowerboardError:
		await session.rollback()
		raise
	user = await session.get(Users, user_id)
	proposal.status = "stopped"
	proposal.finished_at = _now()
	proposal.result_message = f"Stopped early by {user.email if user else 'a user'}."
	session.add(proposal)
	await session.commit()
	_cancel_auto_off(proposal_id)
	return await get_proposal(session, proposal_id)


async def switch_device(session: AsyncSession, device_id: UUID, *, on: bool, user_id: UUID) -> None:
	"""Switch a device on or off by hand. A device switched on stays on until someone switches it off.

	Switching off a device with a run in progress stops that run, so its log entry shows who
	ended it. Raises PowerboardError when the powerboard cannot be reached.
	"""
	target = (
		await session.execute(
			select(Powerboard.host, Device.outlet_num)
			.join(Powerboard, Powerboard.id == Device.powerboard_id)
			.where(Device.id == device_id)
		)
	).one_or_none()
	if target is None:
		raise DeviceNotFoundError("Device not found.")
	if not on:
		run_id = (
			await session.execute(
				select(DeviceProposal.id).where(
					DeviceProposal.device_id == device_id, DeviceProposal.status == "running"
				)
			)
		).scalar_one_or_none()
		if run_id is not None:
			try:
				await stop(session, run_id, user_id)
			except ProposalConflictError:
				logger.info("Run %s ended before it could be stopped; switching the outlet off directly", run_id)
			else:
				return
	await outlets.set_outlet(*target, on=on)


async def resume_auto_off() -> None:
	"""Re-arm switch-off timers for runs that were in progress when the API last stopped."""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		rows = (
			await session.execute(
				select(DeviceProposal.id, DeviceProposal.ends_at).where(DeviceProposal.status == "running")
			)
		).all()
	for proposal_id, ends_at in rows:
		_schedule_auto_off(proposal_id, ends_at)
	if rows:
		logger.info("Re-armed %d device switch-off timer(s)", len(rows))


def cancel_auto_off_timers() -> None:
	"""Cancel the timers on shutdown; resume_auto_off re-arms them on the next start."""
	for task in _auto_off_tasks.values():
		task.cancel()
	_auto_off_tasks.clear()


def _schedule_auto_off(proposal_id: UUID, ends_at: datetime) -> None:
	_cancel_auto_off(proposal_id)
	delay = max(0.0, (ends_at - _now()).total_seconds())
	_auto_off_tasks[proposal_id] = asyncio.create_task(_auto_off(proposal_id, delay), name=f"auto-off-{proposal_id}")


def _cancel_auto_off(proposal_id: UUID) -> None:
	task = _auto_off_tasks.pop(proposal_id, None)
	if task is not None:
		task.cancel()


async def _auto_off(proposal_id: UUID, delay: float) -> None:
	try:
		await asyncio.sleep(delay)
		error: Exception | None = None
		for attempt in range(1, AUTO_OFF_ATTEMPTS + 1):
			try:
				async with AsyncSession(get_engine(), expire_on_commit=False) as session:
					await _finish_run(session, proposal_id)
				return
			except (outlets.PowerboardError, SQLAlchemyError, OSError) as exc:
				error = exc
				logger.warning(
					"Switch-off attempt %d/%d for proposal %s failed: %s", attempt, AUTO_OFF_ATTEMPTS, proposal_id, exc
				)
				if attempt < AUTO_OFF_ATTEMPTS:
					await asyncio.sleep(AUTO_OFF_RETRY_SECONDS)
		async with AsyncSession(get_engine(), expire_on_commit=False) as session:
			await _mark_stuck_on(session, proposal_id, error)
	except Exception:
		logger.exception("Automatic switch-off for proposal %s failed", proposal_id)
	finally:
		if _auto_off_tasks.get(proposal_id) is asyncio.current_task():
			del _auto_off_tasks[proposal_id]


async def _finish_run(session: AsyncSession, proposal_id: UUID) -> None:
	proposal = await _get_for_update(session, proposal_id)
	if proposal.status != "running":
		return
	await outlets.set_outlet(proposal.powerboard_host, proposal.outlet_num, on=False)
	proposal.status = "completed"
	proposal.finished_at = _now()
	session.add(proposal)
	await session.commit()


async def _mark_stuck_on(session: AsyncSession, proposal_id: UUID, error: Exception | None) -> None:
	proposal = await _get_for_update(session, proposal_id)
	if proposal.status != "running":
		return
	device_name = proposal.device_name
	alert_key = f"device_stuck_on_{(proposal.device_id or proposal.id).hex}"
	message = (
		f"Automatic switch-off failed {AUTO_OFF_ATTEMPTS} times ({error}). "
		f"{device_name} may still be on; switch it off at the powerboard."
	)
	proposal.status = "failed"
	proposal.finished_at = _now()
	proposal.result_message = message
	session.add(proposal)
	await session.commit()
	logger.error("Proposal %s: %s", proposal_id, message)
	await alerts.raise_alert(session, alert_key, "critical", f"{device_name} may be stuck on", message)


async def _switch_off_quietly(host: str, outlet_num: int) -> None:
	try:
		await outlets.set_outlet(host, outlet_num, on=False)
	except outlets.PowerboardError:
		logger.exception("Could not switch %s outlet %d back off after a failed approval", host, outlet_num)
