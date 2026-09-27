from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.dependencies.auth import get_current_auth_user
from backend.services.safety_records import create_decision
from backend.services.safety_state import commit_snapshot, effective_command, effective_status_expression
from tests.test_safety_records import session_mock
from tests.test_safety_service import command


@pytest.mark.asyncio
@pytest.mark.parametrize("exists", [True, False])
async def test_auth_checks_account(monkeypatch, exists):
	user_id = uuid4()
	monkeypatch.setattr("backend.dependencies.auth.decode_session_token", lambda token, settings: user_id)
	request = Request({"type": "http", "headers": [(b"cookie", b"session=valid")]})
	settings = MagicMock(SESSION_COOKIE_NAME="session")
	session = MagicMock(get=AsyncMock(return_value=object() if exists else None))
	if exists:
		assert (await get_current_auth_user(request, settings, session)).id == user_id
	else:
		with pytest.raises(HTTPException) as caught:
			await get_current_auth_user(request, settings, session)
		assert caught.value.status_code == 401
	session.get.assert_awaited_once()


@pytest.mark.parametrize(
	"status", ["pending_approval", "approved", "executing", "unknown", "succeeded", "failed", "rejected", "blocked"]
)
def test_expiration_only_applies_to_unstarted_commands(status):
	now = datetime.now(UTC)
	record = command(status=status, expires_at=now)
	result = effective_command(record, now)
	assert result.status == ("expired" if status in {"pending_approval", "approved"} else status)
	assert record.status == status
	record.started_at = now - timedelta(seconds=30)
	assert effective_command(record, now).status == status


def test_expiry_filter_includes_deadline_and_started_guard():
	expression = effective_status_expression(datetime.now(UTC))
	compiled = str(expression)
	assert "CASE WHEN" in compiled
	assert "started_at IS NULL" in compiled
	assert "expires_at <=" in compiled


@pytest.mark.asyncio
async def test_commit_has_no_followup_reads_and_returns_independent_snapshot():
	session = session_mock()
	order = []

	async def flush():
		order.append("flush")

	async def refresh(record):
		order.append("refresh")

	async def commit():
		order.append("commit")

	session.flush.side_effect = flush
	session.refresh.side_effect = refresh
	session.commit.side_effect = commit
	record = command()
	result = await commit_snapshot(session, record)
	assert order == ["flush", "refresh", "commit"]
	assert result is not record
	assert result.request_id == record.request_id


@pytest.mark.asyncio
async def test_refresh_failure_rolls_back_before_commit():
	session = session_mock()
	session.refresh.side_effect = RuntimeError("read failed")
	with pytest.raises(RuntimeError, match="read failed"):
		await create_decision(session, "Warm", "Ventilate")
	session.commit.assert_not_awaited()
	session.rollback.assert_awaited_once()
