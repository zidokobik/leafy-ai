"""Persistence for safety configuration and append-only AI decision records."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.agent_scheduled_job import AgentScheduledJob
from backend.db_models.ai_decisions import AIDecision
from backend.db_models.command_requests import CommandRequest
from backend.db_models.devices import Device
from backend.db_models.safety_rules import SafetyRule
from backend.schemas.ai_decisions import AIDecisionCreate
from backend.schemas.safety_rules import SafetyRuleWrite
from backend.services.safety import SafetyConflictError, SafetyNotFoundError
from backend.services.safety_state import commit_snapshot, effective_command, effective_status_expression


async def get_record(session: AsyncSession, model, record_id: UUID):
	record = await session.get(model, record_id)
	if record is None:
		raise SafetyNotFoundError("Record not found.")
	return effective_command(record, datetime.now(UTC)) if model is CommandRequest else record


async def list_rules(session: AsyncSession, device_id: UUID | None, limit: int, offset: int):
	query = select(SafetyRule)
	if device_id is not None:
		query = query.where(SafetyRule.device_id == device_id)
	return (await session.execute(query.order_by(SafetyRule.rule_id).limit(limit).offset(offset))).scalars().all()


async def save_rule(
	session: AsyncSession,
	*,
	device_id: UUID,
	action_type: str,
	max_duration_seconds: int,
	cooldown_seconds: int,
	enabled: bool,
	rule_id: UUID | None = None,
):
	payload = SafetyRuleWrite(
		device_id=device_id,
		action_type=action_type,
		max_duration_seconds=max_duration_seconds,
		cooldown_seconds=cooldown_seconds,
		enabled=enabled,
	)
	try:
		await get_record(session, Device, device_id)
		record = (
			SafetyRule(**payload.model_dump()) if rule_id is None else await get_record(session, SafetyRule, rule_id)
		)
		for key, value in payload.model_dump().items():
			setattr(record, key, value)
		session.add(record)
		return await commit_snapshot(session, record)
	except IntegrityError as error:
		await session.rollback()
		raise SafetyConflictError("Device/action rule already exists or referenced data changed.") from error
	except Exception:
		await session.rollback()
		raise


async def delete_rule(session: AsyncSession, rule_id: UUID):
	try:
		record = await get_record(session, SafetyRule, rule_id)
		await session.delete(record)
		await session.commit()
	except Exception:
		await session.rollback()
		raise


async def create_decision(session: AsyncSession, summary: str, recommendation: str, schedule_id: UUID | None = None):
	payload = AIDecisionCreate(summary=summary, recommendation=recommendation, schedule_id=schedule_id)
	try:
		if schedule_id is not None:
			await get_record(session, AgentScheduledJob, schedule_id)
		record = AIDecision(**payload.model_dump())
		session.add(record)
		return await commit_snapshot(session, record)
	except IntegrityError as error:
		await session.rollback()
		raise SafetyConflictError("Referenced schedule changed; retry the request.") from error
	except Exception:
		await session.rollback()
		raise


async def list_decisions(session: AsyncSession, schedule_id: UUID | None, limit: int, offset: int):
	query = select(AIDecision)
	if schedule_id is not None:
		query = query.where(AIDecision.schedule_id == schedule_id)
	return (
		(
			await session.execute(
				query.order_by(AIDecision.created_at.desc(), AIDecision.decision_id).limit(limit).offset(offset)
			)
		)
		.scalars()
		.all()
	)


async def list_commands(
	session: AsyncSession,
	device_id: UUID | None,
	decision_id: UUID | None,
	status: str | None,
	limit: int,
	offset: int,
):
	now = datetime.now(UTC)
	query = select(CommandRequest)
	for column, value in [
		(CommandRequest.device_id, device_id),
		(CommandRequest.decision_id, decision_id),
		(effective_status_expression(now), status),
	]:
		if value is not None:
			query = query.where(column == value)
	records = (
		(
			await session.execute(
				query.order_by(CommandRequest.created_at.desc(), CommandRequest.request_id).limit(limit).offset(offset)
			)
		)
		.scalars()
		.all()
	)
	return [effective_command(record, now) for record in records]
