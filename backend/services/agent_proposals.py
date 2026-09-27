"""Chat proposals only: decisions are durable even if subsequent submission fails."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.devices import Device
from backend.db_models.safety_rules import SafetyRule
from backend.schemas.ai_decisions import AIDecisionCreate
from backend.schemas.command_requests import CommandRequestCreate, CommandRequestRead
from backend.services.safety import SafetyNotFoundError, create_command_request
from backend.services.safety_records import create_decision


async def list_proposal_devices(session: AsyncSession, offset: int = 0) -> dict:
	if not 0 <= offset <= 100000:
		raise ValueError("Invalid offset")
	rows = (
		await session.execute(
			select(Device, SafetyRule)
			.outerjoin(
				SafetyRule, (SafetyRule.device_id == Device.device_id) & (SafetyRule.action_type == "run_for_duration")
			)
			.order_by(Device.device_id)
			.offset(offset)
			.limit(51)
		)
	).all()
	return {
		"devices": [
			{
				"deviceId": str(device.device_id),
				"name": device.device_name,
				"type": device.device_type,
				"status": device.status,
				"ruleEnabled": rule.enabled if rule else False,
				"maxDurationSeconds": rule.max_duration_seconds if rule else None,
				"cooldownSeconds": rule.cooldown_seconds if rule else None,
			}
			for device, rule in rows[:50]
		],
		"nextOffset": offset + 50 if len(rows) > 50 else None,
	}


async def propose_operation(
	session: AsyncSession,
	device_id: UUID,
	duration_seconds: int,
	summary: str,
	recommendation: str,
	*,
	schedule_id: UUID | None = None,
) -> dict:
	decision_payload = AIDecisionCreate(summary=summary, recommendation=recommendation, schedule_id=schedule_id)
	proposal = CommandRequestCreate(
		device_id=device_id,
		duration_seconds=duration_seconds,
		reason=decision_payload.recommendation,
		expires_at=datetime.now(UTC) + timedelta(minutes=10),
	)
	if await session.get(Device, proposal.device_id) is None:
		raise SafetyNotFoundError("Device not found; read the device list first.")
	decision = await create_decision(session, **decision_payload.model_dump())
	request = await create_command_request(
		session, **proposal.model_dump(exclude={"decision_id"}), decision_id=decision.decision_id
	)
	return CommandRequestRead.model_validate(request).model_dump(mode="json", by_alias=True)
