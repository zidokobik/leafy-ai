from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.db_models.ai_decisions import AIDecision
from backend.db_models.command_requests import CommandRequest
from backend.services import agent_proposals
from backend.services.agent.agent import build_agent
from backend.services.safety import SafetyNotFoundError


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending_approval", "blocked"])
async def test_proposal_links_decision_and_uses_safety(monkeypatch, status):
	device_id = uuid4()
	decision = AIDecision(summary="Test", recommendation="Run fan")
	record = CommandRequest(
		device_id=device_id,
		decision_id=decision.decision_id,
		duration_seconds=30,
		reason="Run fan",
		status=status,
		expires_at=datetime.now(UTC) + timedelta(minutes=10),
	)
	create = AsyncMock(return_value=decision)
	submit = AsyncMock(return_value=record)
	monkeypatch.setattr(agent_proposals, "create_decision", create)
	monkeypatch.setattr(agent_proposals, "create_command_request", submit)
	session = MagicMock(get=AsyncMock(return_value=object()))
	result = await agent_proposals.propose_operation(session, device_id, 30, "Test", "Run fan")
	assert result["status"] == status
	assert result["requestId"] == str(record.request_id)
	assert submit.call_args.kwargs["decision_id"] == decision.decision_id
	assert "status" not in submit.call_args.kwargs
	assert 590 < (submit.call_args.kwargs["expires_at"] - datetime.now(UTC)).total_seconds() <= 600


@pytest.mark.asyncio
async def test_invalid_proposal_does_not_write(monkeypatch):
	create = AsyncMock()
	monkeypatch.setattr(agent_proposals, "create_decision", create)
	session = MagicMock(get=AsyncMock(return_value=None))
	with pytest.raises(ValidationError):
		await agent_proposals.propose_operation(session, uuid4(), -1, "Test", "Run fan")
	with pytest.raises(SafetyNotFoundError):
		await agent_proposals.propose_operation(session, uuid4(), 30, "Test", "Run fan")
	create.assert_not_awaited()


def test_agent_builds_with_and_without_proposal_tools():
	assert build_agent() is not None
	assert build_agent(allow_proposals=True) is not None
	assert build_agent(allow_proposals=True, schedule_id=uuid4()) is not None


@pytest.mark.asyncio
async def test_scheduled_tool_binds_source_and_blocks_repeat(monkeypatch):
	from backend.services.agent.agent_tools import proposals

	monkeypatch.setattr(proposals.ai, "tool", lambda function: function)
	monkeypatch.setattr(proposals, "get_engine", lambda: None)
	context = MagicMock()
	context.__aenter__ = AsyncMock(return_value=object())
	context.__aexit__ = AsyncMock(return_value=False)
	monkeypatch.setattr(proposals, "AsyncSession", lambda *args, **kwargs: context)
	submit = AsyncMock(return_value={"status": "pending_approval"})
	monkeypatch.setattr(proposals, "propose_operation", submit)
	schedule_id, device_id = uuid4(), uuid4()
	tool = proposals.scheduled_proposal_tool(schedule_id)
	assert (await tool(device_id, 30, "Test", "Run fan"))["status"] == "pending_approval"
	assert submit.call_args.kwargs["schedule_id"] == schedule_id
	assert "error" in await tool(device_id, 30, "Test", "Run fan")
	submit.assert_awaited_once()


@pytest.mark.asyncio
async def test_schedule_id_is_recorded_on_decision(monkeypatch):
	schedule_id, device_id = uuid4(), uuid4()
	decision = AIDecision(summary="Test", recommendation="Run fan", schedule_id=schedule_id)
	create = AsyncMock(return_value=decision)
	record = CommandRequest(
		device_id=device_id,
		decision_id=decision.decision_id,
		duration_seconds=30,
		reason="Run fan",
		expires_at=datetime.now(UTC) + timedelta(minutes=10),
	)
	monkeypatch.setattr(agent_proposals, "create_decision", create)
	monkeypatch.setattr(agent_proposals, "create_command_request", AsyncMock(return_value=record))
	await agent_proposals.propose_operation(
		MagicMock(get=AsyncMock(return_value=object())), device_id, 30, "Test", "Run fan", schedule_id=schedule_id
	)
	assert create.call_args.kwargs["schedule_id"] == schedule_id
