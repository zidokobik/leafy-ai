from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from backend.db_models.agent_scheduled_job import AgentScheduledJob
from backend.db_models.ai_decisions import AIDecision
from backend.db_models.command_requests import CommandRequest
from backend.db_models.devices import Device
from backend.db_models.safety_rules import SafetyRule
from backend.db_models.users import Users
from backend.schemas.ai_decisions import AIDecisionCreate
from backend.schemas.command_requests import CommandRequestCreate, CommandRequestRead, CommandReviewRequest
from backend.schemas.safety_rules import SafetyRuleWrite


def request_payload():
	return {
		"deviceId": str(uuid4()),
		"durationSeconds": 30,
		"reason": "Run the fan",
		"expiresAt": datetime.now(UTC) + timedelta(minutes=10),
	}


def test_valid_request_and_camel_case():
	request = CommandRequestCreate.model_validate(request_payload())
	assert request.duration_seconds == 30
	assert request.model_dump(by_alias=True)["actionType"] == "run_for_duration"


@pytest.mark.parametrize(
	("field", "value"),
	[
		("durationSeconds", 0),
		("durationSeconds", -1),
		("durationSeconds", True),
		("durationSeconds", "30"),
		("durationSeconds", 2147483648),
		("reason", "  "),
		("actionType", "unrestricted_command"),
		("status", "approved"),
		("reviewedBy", str(uuid4())),
		("expiresAt", datetime(2020, 1, 1, tzinfo=UTC)),
		("expiresAt", "2099-01-01T00:00:00"),
	],
)
def test_invalid_request(field, value):
	payload = request_payload()
	payload[field] = value
	with pytest.raises(ValidationError):
		CommandRequestCreate.model_validate(payload)


def test_expired_record_can_be_read():
	now = datetime.now(UTC)
	record = CommandRequest(
		device_id=uuid4(),
		duration_seconds=30,
		reason="Fan",
		created_at=now - timedelta(hours=2),
		expires_at=now - timedelta(hours=1),
		status="expired",
	)
	result = CommandRequestRead.model_validate(record)
	assert result.status == "expired"
	assert result.model_dump(by_alias=True)["requestId"] == record.request_id


@pytest.mark.parametrize("field,value", [("maxDurationSeconds", 0), ("cooldownSeconds", -1), ("enabled", "true")])
def test_invalid_rule(field, value):
	payload = {"deviceId": str(uuid4()), "maxDurationSeconds": 60, field: value}
	with pytest.raises(ValidationError):
		SafetyRuleWrite.model_validate(payload)


def test_decision_requires_nonblank_text():
	with pytest.raises(ValidationError):
		AIDecisionCreate(summary=" ", recommendation="Run fan")
	assert AIDecisionCreate(summary=" Warm ", recommendation="Run fan").summary == "Warm"


def test_review_cannot_supply_identity_or_execution_status():
	assert CommandReviewRequest(action="approve").action == "approve"
	for payload in [{"action": "succeeded"}, {"action": "approve", "reviewedBy": str(uuid4())}]:
		with pytest.raises(ValidationError):
			CommandReviewRequest.model_validate(payload)


def test_models_compile_with_resolved_foreign_keys_without_database():
	# Import all referenced models explicitly; no connection or table creation occurs.
	for model in [Users, AgentScheduledJob, Device, SafetyRule, AIDecision, CommandRequest]:
		table = model.__table__
		for foreign_key in table.foreign_keys:
			assert foreign_key.column is not None
		assert str(CreateTable(table).compile(dialect=postgresql.dialect()))
	assert CommandRequest.__table__.c.expires_at.type.timezone
	assert next(iter(AIDecision.__table__.c.schedule_id.foreign_keys)).ondelete == "SET NULL"
	assert next(iter(CommandRequest.__table__.c.reviewed_by.foreign_keys)).ondelete == "SET NULL"
