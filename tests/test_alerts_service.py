from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from backend.db_models.alerts import Alert
from backend.services.alerts import AlertNotFoundError, dismiss_alert, raise_alert, resolve_alert


def session_mock(executed_alert: Alert | None = None):
	session = MagicMock()
	result = MagicMock()
	result.scalars.return_value.one.return_value = executed_alert
	session.execute = AsyncMock(return_value=result)
	session.get = AsyncMock(return_value=None)
	session.commit = AsyncMock()
	session.add = MagicMock()
	return session


@pytest.mark.asyncio
async def test_raise_alert_rejects_invalid_input():
	session = session_mock()
	for key, title, message in [
		("Water pH High", "t", "m"),  # not snake_case
		("x" * 65, "t", "m"),
		("water_ph_high", "  ", "m"),
		("water_ph_high", "t", "m" * 4001),
	]:
		with pytest.raises(ValueError):
			await raise_alert(session, key, "warning", title, message)
	session.execute.assert_not_awaited()
	session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_raise_alert_upserts_and_commits():
	stored = Alert(alert_key="water_ph_high", severity="warning", title="pH high", message="pH 7.4", occurrences=2)
	session = session_mock(stored)
	alert = await raise_alert(session, "water_ph_high", "warning", " pH high ", " pH 7.4 ")
	assert alert is stored
	statement = session.execute.await_args.args[0]
	compiled = str(statement.compile())
	assert "ON CONFLICT (alert_key) WHERE status = 'active' DO UPDATE" in compiled
	assert "occurrences + " in compiled
	assert "dismissed_at" in compiled, "a re-raise must resurface a dismissed alert"
	session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_missing_alert():
	session = session_mock()
	with pytest.raises(AlertNotFoundError):
		await resolve_alert(session, uuid4(), "user")
	session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_dismiss_hides_without_resolving():
	alert = Alert(alert_key="water_ph_high", severity="warning", title="pH high", message="pH 7.4")
	session = session_mock()
	session.get.return_value = alert

	dismissed = await dismiss_alert(session, uuid4())
	assert dismissed.status == "active"
	assert dismissed.resolved_at is None and dismissed.resolved_by is None
	assert dismissed.dismissed_at is not None
	session.commit.assert_awaited_once()

	# Idempotent for already dismissed and for resolved alerts.
	first_dismissed_at = dismissed.dismissed_at
	assert (await dismiss_alert(session, uuid4())).dismissed_at == first_dismissed_at
	alert.status = "resolved"
	alert.dismissed_at = None
	assert (await dismiss_alert(session, uuid4())).dismissed_at is None
	session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_dismiss_missing_alert():
	session = session_mock()
	with pytest.raises(AlertNotFoundError):
		await dismiss_alert(session, uuid4())
	session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_alert_sets_resolution_once():
	alert = Alert(alert_key="water_ph_high", severity="warning", title="pH high", message="pH 7.4")
	session = session_mock()
	session.get.return_value = alert

	resolved = await resolve_alert(session, uuid4(), "agent")
	assert resolved.status == "resolved"
	assert resolved.resolved_by == "agent"
	assert resolved.resolved_at is not None
	assert resolved.updated_at == resolved.resolved_at
	session.commit.assert_awaited_once()

	# Idempotent: a second resolve changes nothing and does not commit again.
	first_resolved_at = resolved.resolved_at
	again = await resolve_alert(session, uuid4(), "user")
	assert again.resolved_by == "agent"
	assert again.resolved_at == first_resolved_at
	session.commit.assert_awaited_once()
