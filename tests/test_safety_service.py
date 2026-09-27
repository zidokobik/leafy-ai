from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from backend.db_models.command_requests import CommandRequest
from backend.db_models.safety_rules import SafetyRule
from backend.services.safety import (
	SafetyConflictError,
	SafetyNotFoundError,
	create_command_request,
	evaluate_safety,
	review_command_request,
)


def command(**values):
	return CommandRequest(
		**{
			"device_id": uuid4(),
			"duration_seconds": 30,
			"reason": "Fan",
			"expires_at": datetime.now(UTC) + timedelta(hours=1),
			**values,
		}
	)


def rule(**values):
	return SafetyRule(**{"device_id": uuid4(), "max_duration_seconds": 60, "cooldown_seconds": 120, **values})


def session_with(*results):
	session = MagicMock()
	session.get = AsyncMock(return_value=object())
	session.commit = AsyncMock()
	session.flush = AsyncMock()
	session.rollback = AsyncMock()
	session.refresh = AsyncMock()
	session.execute = AsyncMock(side_effect=results)
	return session


def result(value):
	item = MagicMock()
	item.scalar_one_or_none.return_value = value
	item.scalars.return_value.all.return_value = value
	return item


@pytest.mark.parametrize("active_rule", [None, rule(enabled=False), rule(max_duration_seconds=10)])
def test_rule_blocks(active_rule):
	assert evaluate_safety(active_rule, "run_for_duration", 30, [], datetime.now(UTC))


@pytest.mark.parametrize("status", ["executing", "unknown", "approved", "succeeded", "failed"])
def test_busy_or_incomplete_history_blocks(status):
	assert evaluate_safety(rule(), "run_for_duration", 30, [command(status=status)], datetime.now(UTC))


def test_cooldown_uses_completion_including_failed_execution():
	now = datetime.now(UTC)
	previous = command(status="failed", started_at=now - timedelta(minutes=5), finished_at=now - timedelta(seconds=119))
	assert evaluate_safety(rule(), "run_for_duration", 30, [previous], now)
	previous.finished_at = now - timedelta(seconds=120)
	assert evaluate_safety(rule(), "run_for_duration", 30, [previous], now) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("active_rule, expected", [(rule(), "pending_approval"), (None, "blocked")])
async def test_create_persists_validation_result(active_rule, expected):
	session = session_with(result(object()), result(active_rule), result([]))
	request = await create_command_request(
		session,
		device_id=uuid4(),
		duration_seconds=30,
		reason="Fan",
		expires_at=datetime.now(UTC) + timedelta(minutes=10),
	)
	assert request.status == expected
	assert request.started_at is None
	session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_device_rolls_back():
	session = session_with(result(None))
	with pytest.raises(SafetyNotFoundError):
		await create_command_request(
			session,
			device_id=uuid4(),
			duration_seconds=30,
			reason="Fan",
			expires_at=datetime.now(UTC) + timedelta(minutes=10),
		)
	session.rollback.assert_awaited_once()
	session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("active_rule, expected", [(rule(), "approved"), (rule(enabled=False), "blocked")])
async def test_approval_rechecks_latest_rule(active_rule, expected):
	request = command()
	session = session_with(result(request), result(object()), result(active_rule), result([]))
	reviewer = uuid4()
	updated = await review_command_request(session, request.request_id, reviewer, "approve")
	assert updated.status == expected
	assert updated.reviewed_by == reviewer
	assert updated.started_at is None
	assert updated.finished_at is None
	session.commit.assert_awaited_once()
	assert "FOR UPDATE" in str(session.execute.call_args_list[0].args[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("expired, expected", [(True, "expired"), (False, "rejected")])
async def test_rejection_and_expiration(expired, expected):
	request = command()
	if expired:
		request.expires_at = datetime.now(UTC) - timedelta(seconds=1)
	session = session_with(result(request))
	assert (await review_command_request(session, request.request_id, uuid4(), "reject")).status == expected
	assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_cannot_review_twice():
	request = command(status="approved")
	session = session_with(result(request))
	with pytest.raises(SafetyConflictError):
		await review_command_request(session, request.request_id, uuid4(), "reject")
	session.rollback.assert_awaited_once()
	session.commit.assert_not_awaited()
