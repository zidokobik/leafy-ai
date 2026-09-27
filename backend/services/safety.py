"""Software-only command validation. No hardware calls or agent tools live here.

Write functions commit on success and roll back on failure. Use a dedicated session
without unrelated pending changes. Review callers must authenticate and authorize
the human reviewer; never expose review_command_request as an AI tool.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.agent_scheduled_job import AgentScheduledJob  # noqa: F401 -- register decision FK target
from backend.db_models.ai_decisions import AIDecision
from backend.db_models.command_requests import CommandRequest
from backend.db_models.devices import Device
from backend.db_models.safety_rules import SafetyRule
from backend.db_models.users import Users
from backend.schemas.command_requests import CommandRequestCreate, CommandReviewRequest
from backend.services.safety_state import commit_snapshot, effective_command


class SafetyNotFoundError(ValueError):
	"""A referenced device, decision, request or reviewer does not exist."""


class SafetyConflictError(ValueError):
	"""The request is no longer awaiting review."""


def evaluate_safety(
	rule: SafetyRule | None,
	action_type: str,
	duration_seconds: int,
	history: list[CommandRequest],
	now: datetime,
) -> str | None:
	"""Return a blocking reason, or None. Cooldown begins at actual completion."""
	if rule is None or not rule.enabled:
		return "No enabled safety rule for this device and action."
	if action_type != "run_for_duration" or rule.action_type != action_type:
		return "Unsupported action."
	if type(duration_seconds) is not int or not 0 < duration_seconds <= rule.max_duration_seconds:
		return "Duration exceeds the allowed range."
	for previous in history:
		if previous.status in {"executing", "unknown"}:
			return "Device execution is active or its outcome is unknown."
		if previous.status == "approved" and previous.expires_at > now:
			return "Device already has an approved command awaiting execution."
		if previous.started_at is not None or previous.status in {"succeeded", "failed"}:
			if previous.started_at is None or previous.finished_at is None:
				return "Previous execution has incomplete timing records."
			if previous.finished_at < previous.started_at:
				return "Previous execution has invalid timing records."
			if now < previous.finished_at + timedelta(seconds=rule.cooldown_seconds):
				return "Device cooldown has not elapsed."
	return None


async def _check(session: AsyncSession, request: CommandRequest, now: datetime) -> str | None:
	# Serialize proposals/reviews for the same device, including different actions.
	device = (
		await session.execute(select(Device).where(Device.device_id == request.device_id).with_for_update())
	).scalar_one_or_none()
	if device is None:
		raise SafetyNotFoundError("Device not found.")
	rule = (
		await session.execute(
			select(SafetyRule)
			.where(
				SafetyRule.device_id == request.device_id,
				SafetyRule.action_type == request.action_type,
			)
			.with_for_update()
			.execution_options(populate_existing=True)
		)
	).scalar_one_or_none()
	history = (
		(
			await session.execute(
				select(CommandRequest)
				.where(
					CommandRequest.device_id == request.device_id,
					CommandRequest.request_id != request.request_id,
				)
				.execution_options(populate_existing=True)
			)
		)
		.scalars()
		.all()
	)
	return evaluate_safety(rule, request.action_type, request.duration_seconds, history, now)


async def create_command_request(
	session: AsyncSession,
	*,
	device_id: UUID,
	duration_seconds: int,
	reason: str,
	expires_at: datetime,
	action_type: str = "run_for_duration",
	decision_id: UUID | None = None,
) -> CommandRequest:
	# Validate here too: internal callers do not pass through FastAPI schemas.
	payload = CommandRequestCreate(
		device_id=device_id,
		duration_seconds=duration_seconds,
		reason=reason,
		expires_at=expires_at,
		action_type=action_type,
		decision_id=decision_id,
	)
	try:
		if decision_id is not None and await session.get(AIDecision, decision_id) is None:
			raise SafetyNotFoundError("AI decision not found.")
		request = CommandRequest(**payload.model_dump())
		blocked_reason = await _check(session, request, datetime.now(UTC))
		# Locks may have taken time to acquire. Never queue an already expired command.
		if request.expires_at <= datetime.now(UTC):
			request.status = "expired"
			request.result_message = "Request expired before validation completed."
		else:
			request.status = "blocked" if blocked_reason else "pending_approval"
			request.result_message = blocked_reason or "Safety checks passed; awaiting human approval."
		session.add(request)
		return await commit_snapshot(session, request)
	except Exception:
		await session.rollback()
		raise


async def review_command_request(
	session: AsyncSession,
	request_id: UUID,
	reviewer_id: UUID,
	action: str,
) -> CommandRequest:
	"""Trusted human-only entry point. Approval never performs hardware execution."""
	CommandReviewRequest(action=action)
	try:
		if await session.get(Users, reviewer_id) is None:
			raise SafetyNotFoundError("Reviewer not found.")
		request = (
			await session.execute(
				select(CommandRequest)
				.where(CommandRequest.request_id == request_id)
				.with_for_update()
				.execution_options(populate_existing=True)
			)
		).scalar_one_or_none()
		if request is None:
			raise SafetyNotFoundError("Command request not found.")
		effective = effective_command(request, datetime.now(UTC))
		if effective.status == "expired" and request.status != "expired":
			request.status = effective.status
			request.result_message = effective.result_message
			return await commit_snapshot(session, request)
		if request.status != "pending_approval":
			raise SafetyConflictError("Only pending requests can be reviewed.")
		now = datetime.now(UTC)
		if request.expires_at <= now:
			request.status = "expired"
			request.result_message = "Request expired before review."
		else:
			blocked_reason = await _check(session, request, now) if action == "approve" else None
			now = datetime.now(UTC)
			if request.expires_at <= now:
				request.status = "expired"
				request.result_message = "Request expired during review."
			else:
				request.reviewed_by = reviewer_id
				request.reviewed_at = now
				request.status = "blocked" if blocked_reason else ("approved" if action == "approve" else "rejected")
				request.result_message = blocked_reason or (
					"Approved by human; hardware execution is not connected."
					if action == "approve"
					else "Rejected by human."
				)
		session.add(request)
		return await commit_snapshot(session, request)
	except Exception:
		await session.rollback()
		raise
