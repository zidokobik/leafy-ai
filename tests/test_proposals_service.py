from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from backend.db_models.device_proposals import DeviceProposal
from backend.db_models.devices import Device
from backend.db_models.users import Users
from backend.services import outlets, proposals
from backend.services.devices import DeviceNotFoundError

HOST = "192.168.1.101"


def session_mock():
	session = MagicMock()
	session.add = MagicMock()
	session.commit = AsyncMock()
	session.rollback = AsyncMock()
	session.execute = AsyncMock(return_value=MagicMock())
	session.get = AsyncMock(return_value=None)
	return session


def pending(**overrides) -> DeviceProposal:
	now = datetime.now(UTC)
	values = {
		"device_id": uuid4(),
		"device_name": "Fan",
		"duration_seconds": 600,
		"reason": "Humidity 88% for 2 h.",
		"expires_at": now + timedelta(minutes=30),
	}
	return DeviceProposal(**(values | overrides))


def running(**overrides) -> DeviceProposal:
	started = datetime.now(UTC)
	values = {
		"status": "running",
		"powerboard_host": HOST,
		"outlet_num": 2,
		"started_at": started,
		"ends_at": started + timedelta(minutes=10),
	}
	return pending(**(values | overrides))


@pytest.fixture
def hardware(monkeypatch):
	"""Stub the database helpers, the outlet switch and the auto-off timers."""
	stubs = MagicMock()
	stubs.set_outlet = AsyncMock()
	stubs.schedule = MagicMock()
	stubs.cancel = MagicMock()
	stubs.read = AsyncMock(return_value="read model")
	monkeypatch.setattr(proposals, "_expire_stale", AsyncMock())
	monkeypatch.setattr(proposals.outlets, "set_outlet", stubs.set_outlet)
	monkeypatch.setattr(proposals, "_schedule_auto_off", stubs.schedule)
	monkeypatch.setattr(proposals, "_cancel_auto_off", stubs.cancel)
	monkeypatch.setattr(proposals, "get_proposal", stubs.read)
	return stubs


def lock_returns(monkeypatch, proposal: DeviceProposal):
	monkeypatch.setattr(proposals, "_get_for_update", AsyncMock(return_value=proposal))


@pytest.mark.asyncio
async def test_propose_rejects_invalid_input(hardware):
	session = session_mock()
	for duration, reason in [(0, "ok"), (86_401, "ok"), (60, "   "), (60, "x" * 2001)]:
		with pytest.raises(ValueError):
			await proposals.propose_run(session, uuid4(), duration, reason)
	session.get.assert_not_awaited()

	with pytest.raises(DeviceNotFoundError):
		await proposals.propose_run(session, uuid4(), 60, "Humidity high")
	session.add.assert_not_called()


@pytest.mark.asyncio
async def test_propose_refuses_a_second_open_proposal(hardware):
	session = session_mock()
	session.get.return_value = Device(name="Fan", device_type="fan", powerboard_id=uuid4(), outlet_num=1)
	session.execute.return_value.scalar_one_or_none.return_value = running()
	with pytest.raises(proposals.ProposalConflictError, match="already has a running proposal"):
		await proposals.propose_run(session, uuid4(), 60, "Humidity high")
	session.add.assert_not_called()


@pytest.mark.asyncio
async def test_propose_records_a_pending_proposal(hardware):
	session = session_mock()
	device = Device(name="Fan", device_type="fan", powerboard_id=uuid4(), outlet_num=1)
	session.get.return_value = device
	session.execute.return_value.scalar_one_or_none.return_value = None
	schedule_id = uuid4()

	result = await proposals.propose_run(session, device.id, 600, "  Humidity 88% for 2 h.  ", schedule_id=schedule_id)
	assert result.status == "pending"
	assert result.device_name == "Fan" and result.reason == "Humidity 88% for 2 h."
	assert result.schedule_id == schedule_id
	assert result.expires_at - result.created_at == proposals.PROPOSAL_TTL
	session.commit.assert_awaited_once()
	hardware.set_outlet.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_switches_on_and_arms_the_timer(monkeypatch, hardware):
	proposal = pending()
	lock_returns(monkeypatch, proposal)
	session = session_mock()
	session.execute.return_value.one_or_none.return_value = (HOST, 2)
	reviewer = uuid4()

	assert await proposals.approve(session, proposal.id, reviewer) == "read model"
	hardware.set_outlet.assert_awaited_once_with(HOST, 2, on=True)
	assert proposal.status == "running"
	assert proposal.reviewed_by == reviewer and proposal.reviewed_at is not None
	assert (proposal.powerboard_host, proposal.outlet_num) == (HOST, 2)
	assert proposal.ends_at - proposal.started_at == timedelta(seconds=600)
	hardware.schedule.assert_called_once_with(proposal.id, proposal.ends_at)


@pytest.mark.asyncio
async def test_approve_records_a_powerboard_failure(monkeypatch, hardware):
	proposal = pending()
	lock_returns(monkeypatch, proposal)
	session = session_mock()
	session.execute.return_value.one_or_none.return_value = (HOST, 2)
	hardware.set_outlet.side_effect = outlets.PowerboardError(f"Powerboard {HOST} did not respond.")

	await proposals.approve(session, proposal.id, uuid4())
	assert proposal.status == "failed"
	assert "did not respond" in proposal.result_message
	assert proposal.started_at is None
	session.commit.assert_awaited_once()
	hardware.schedule.assert_not_called()


@pytest.mark.asyncio
async def test_only_pending_proposals_can_be_reviewed(monkeypatch, hardware):
	lock_returns(monkeypatch, pending(status="expired"))
	session = session_mock()
	with pytest.raises(proposals.ProposalConflictError, match="already expired"):
		await proposals.approve(session, uuid4(), uuid4())
	with pytest.raises(proposals.ProposalConflictError):
		await proposals.reject(session, uuid4(), uuid4())
	hardware.set_outlet.assert_not_awaited()
	session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_switches_back_off_when_saving_fails(monkeypatch, hardware):
	lock_returns(monkeypatch, pending())
	session = session_mock()
	session.execute.return_value.one_or_none.return_value = (HOST, 2)
	session.commit.side_effect = RuntimeError("database went away")

	with pytest.raises(RuntimeError):
		await proposals.approve(session, uuid4(), uuid4())
	assert [call.kwargs["on"] for call in hardware.set_outlet.await_args_list] == [True, False]
	hardware.schedule.assert_not_called()


@pytest.mark.asyncio
async def test_reject(monkeypatch, hardware):
	proposal = pending()
	lock_returns(monkeypatch, proposal)
	await proposals.reject(session_mock(), proposal.id, uuid4())
	assert proposal.status == "rejected" and proposal.reviewed_at is not None
	hardware.set_outlet.assert_not_awaited()


@pytest.mark.asyncio
async def test_stop_switches_off_early(monkeypatch, hardware):
	proposal = running()
	lock_returns(monkeypatch, proposal)
	session = session_mock()
	session.get.return_value = Users(email="grower@example.com", password_hash="x", created_at=datetime.now(UTC))

	await proposals.stop(session, proposal.id, uuid4())
	hardware.set_outlet.assert_awaited_once_with(HOST, 2, on=False)
	assert proposal.status == "stopped" and proposal.finished_at is not None
	assert "grower@example.com" in proposal.result_message
	hardware.cancel.assert_called_once_with(proposal.id)


@pytest.mark.asyncio
async def test_failed_stop_keeps_the_run_and_its_timer(monkeypatch, hardware):
	proposal = running()
	lock_returns(monkeypatch, proposal)
	session = session_mock()
	hardware.set_outlet.side_effect = outlets.PowerboardError("unreachable")

	with pytest.raises(outlets.PowerboardError):
		await proposals.stop(session, proposal.id, uuid4())
	assert proposal.status == "running"
	session.rollback.assert_awaited_once()
	hardware.cancel.assert_not_called()


def switch_session(run_id=None):
	"""A session whose first query finds the device's outlet and whose second finds its running proposal."""
	session = session_mock()
	target, run = MagicMock(), MagicMock()
	target.one_or_none.return_value = (HOST, 3)
	run.scalar_one_or_none.return_value = run_id
	session.execute.side_effect = [target, run]
	return session


@pytest.mark.asyncio
async def test_manual_switch_targets_the_device_outlet(monkeypatch, hardware):
	stop = AsyncMock()
	monkeypatch.setattr(proposals, "stop", stop)

	await proposals.switch_device(switch_session(), uuid4(), on=True, user_id=uuid4())
	hardware.set_outlet.assert_awaited_with(HOST, 3, on=True)
	await proposals.switch_device(switch_session(), uuid4(), on=False, user_id=uuid4())
	hardware.set_outlet.assert_awaited_with(HOST, 3, on=False)
	stop.assert_not_awaited()

	session = session_mock()
	session.execute.return_value.one_or_none.return_value = None
	with pytest.raises(DeviceNotFoundError):
		await proposals.switch_device(session, uuid4(), on=True, user_id=uuid4())


@pytest.mark.asyncio
async def test_manual_switch_off_stops_a_run_in_progress(monkeypatch, hardware):
	run_id, user_id = uuid4(), uuid4()
	stop = AsyncMock()
	monkeypatch.setattr(proposals, "stop", stop)

	await proposals.switch_device(switch_session(run_id), uuid4(), on=False, user_id=user_id)
	stop.assert_awaited_once()
	assert stop.await_args.args[1:] == (run_id, user_id)
	hardware.set_outlet.assert_not_awaited()

	# A run that ended in the meantime cannot be stopped; the outlet is switched off directly.
	stop.side_effect = proposals.ProposalConflictError("already completed")
	await proposals.switch_device(switch_session(run_id), uuid4(), on=False, user_id=user_id)
	hardware.set_outlet.assert_awaited_once_with(HOST, 3, on=False)


@pytest.mark.asyncio
async def test_finish_run_switches_off_only_running_proposals(monkeypatch, hardware):
	proposal = running()
	lock_returns(monkeypatch, proposal)
	await proposals._finish_run(session_mock(), proposal.id)
	hardware.set_outlet.assert_awaited_once_with(HOST, 2, on=False)
	assert proposal.status == "completed" and proposal.finished_at is not None

	lock_returns(monkeypatch, running(status="stopped"))
	await proposals._finish_run(session_mock(), uuid4())
	hardware.set_outlet.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_off_retries_then_flags_the_device_as_stuck_on(monkeypatch):
	@asynccontextmanager
	async def fake_session(*args, **kwargs):
		yield session_mock()

	monkeypatch.setattr(proposals, "AsyncSession", fake_session)
	monkeypatch.setattr(proposals, "get_engine", lambda: None)
	monkeypatch.setattr(proposals, "AUTO_OFF_ATTEMPTS", 3)
	monkeypatch.setattr(proposals, "AUTO_OFF_RETRY_SECONDS", 0)
	error = outlets.PowerboardError("unreachable")
	finish = AsyncMock(side_effect=error)
	stuck = AsyncMock()
	monkeypatch.setattr(proposals, "_finish_run", finish)
	monkeypatch.setattr(proposals, "_mark_stuck_on", stuck)

	await proposals._auto_off(uuid4(), 0)
	assert finish.await_count == 3
	stuck.assert_awaited_once()
	assert stuck.await_args.args[2] is error


@pytest.mark.asyncio
async def test_stuck_on_marks_failed_and_raises_a_critical_alert(monkeypatch):
	proposal = running()
	lock_returns(monkeypatch, proposal)
	raise_alert = AsyncMock()
	monkeypatch.setattr(proposals.alerts, "raise_alert", raise_alert)

	await proposals._mark_stuck_on(session_mock(), proposal.id, outlets.PowerboardError("unreachable"))
	assert proposal.status == "failed"
	assert "may still be on" in proposal.result_message
	key, severity = raise_alert.await_args.args[1:3]
	assert key == f"device_stuck_on_{proposal.device_id.hex}"
	assert severity == "critical"


@pytest.mark.asyncio
async def test_scheduled_tool_binds_the_schedule_and_hides_the_reviewer(monkeypatch):
	from backend.services.agent.agent_tools import devices as device_tools

	monkeypatch.setattr(device_tools.ai, "tool", lambda function: function)

	@asynccontextmanager
	async def fake_session(*args, **kwargs):
		yield session_mock()

	monkeypatch.setattr(device_tools, "AsyncSession", fake_session)
	monkeypatch.setattr(device_tools, "get_engine", lambda: None)
	proposal = proposals._to_read(pending(reviewed_by=uuid4()), "grower@example.com")
	propose = AsyncMock(return_value=proposal)
	monkeypatch.setattr(device_tools.proposal_service, "propose_run", propose)
	schedule_id = uuid4()

	tool = device_tools.propose_device_run_tool(schedule_id)
	result = await tool(uuid4(), 600, "Humidity high")
	assert propose.await_args.kwargs["schedule_id"] == schedule_id
	assert result["status"] == "pending"
	assert "reviewerEmail" not in result and "reviewedBy" not in result
