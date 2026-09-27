from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from backend.services.safety import SafetyConflictError, SafetyNotFoundError
from backend.services.safety_records import create_decision, delete_rule, save_rule


def session_mock():
	session = MagicMock()
	session.get = AsyncMock(return_value=object())
	session.commit = AsyncMock()
	session.flush = AsyncMock()
	session.refresh = AsyncMock()
	session.rollback = AsyncMock()
	session.delete = AsyncMock()
	return session


@pytest.mark.asyncio
async def test_rule_creation_and_duplicate_rollback():
	session = session_mock()
	kwargs = {
		"device_id": uuid4(),
		"action_type": "run_for_duration",
		"max_duration_seconds": 60,
		"cooldown_seconds": 120,
		"enabled": True,
	}
	rule = await save_rule(session, **kwargs)
	assert rule.max_duration_seconds == 60
	session.commit.assert_awaited_once()
	session.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
	with pytest.raises(SafetyConflictError):
		await save_rule(session, **kwargs)
	session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_rule_does_not_delete():
	session = session_mock()
	session.get.return_value = None
	with pytest.raises(SafetyNotFoundError):
		await delete_rule(session, uuid4())
	session.delete.assert_not_awaited()
	session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_decision_creation_and_missing_schedule():
	session = session_mock()
	decision = await create_decision(session, " Warm ", "Ventilate")
	assert decision.summary == "Warm"
	session.get.assert_not_awaited()
	session.get.return_value = None
	with pytest.raises(SafetyNotFoundError):
		await create_decision(session, "Warm", "Ventilate", uuid4())
	session.rollback.assert_awaited_once()
