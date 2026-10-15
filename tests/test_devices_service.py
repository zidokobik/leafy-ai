from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from backend.db_models.devices import Device, Powerboard
from backend.services import devices, outlets


def session_mock():
	session = MagicMock()
	session.add = MagicMock()
	session.commit = AsyncMock()
	session.rollback = AsyncMock()
	session.delete = AsyncMock()
	session.execute = AsyncMock()
	session.get = AsyncMock(return_value=None)
	session.scalar = AsyncMock(return_value=0)
	return session


@pytest.mark.asyncio
async def test_duplicate_host_is_a_conflict():
	session = session_mock()
	session.commit.side_effect = IntegrityError("INSERT", {}, Exception("duplicate key"))
	with pytest.raises(devices.DeviceConflictError, match="already uses the host"):
		await devices.create_powerboard(session, "Rack 1", "192.168.1.101")
	session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_powerboard_with_devices_cannot_be_deleted():
	session = session_mock()
	session.get.return_value = Powerboard(name="Rack 1", host="192.168.1.101")
	session.scalar.return_value = 2
	with pytest.raises(devices.DeviceConflictError, match="2 device"):
		await devices.delete_powerboard(session, uuid4())
	session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_device_needs_an_existing_powerboard():
	session = session_mock()
	with pytest.raises(devices.PowerboardNotFoundError):
		await devices.create_device(session, "Fan", "fan", uuid4(), 1)
	session.add.assert_not_called()


@pytest.mark.asyncio
async def test_taken_outlet_is_a_conflict():
	session = session_mock()
	session.get.return_value = Powerboard(name="Rack 1", host="192.168.1.101")
	session.commit.side_effect = IntegrityError("INSERT", {}, Exception("duplicate key"))
	with pytest.raises(devices.DeviceConflictError, match="Outlet 3"):
		await devices.create_device(session, "Fan", "fan", uuid4(), 3)


@pytest.mark.asyncio
async def test_deleting_a_device_rejects_its_pending_proposal():
	session = session_mock()
	device = Device(name="Fan", device_type="fan", powerboard_id=uuid4(), outlet_num=1)
	session.get.return_value = device
	await devices.delete_device(session, device.id)

	statement = session.execute.await_args.args[0]
	assert str(statement).startswith("UPDATE device_proposals")
	params = statement.compile().params
	assert params["status"] == "rejected"
	assert params["status_1"] == "pending"
	session.delete.assert_awaited_once_with(device)
	session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unreachable_powerboard_reports_an_error_state(monkeypatch):
	online = Powerboard(name="Rack 1", host="192.168.1.101")
	offline = Powerboard(name="Rack 2", host="192.168.1.102")
	monkeypatch.setattr(devices, "list_powerboards", AsyncMock(return_value=[online, offline]))

	async def read_outlets(host):
		if host == offline.host:
			raise outlets.PowerboardError("Powerboard 192.168.1.102 did not respond.")
		return [True, False]

	monkeypatch.setattr(devices.outlets, "read_outlets", read_outlets)
	states = await devices.read_powerboard_states(session_mock())
	assert states[0].powerboard_id == online.id and states[0].outlets == [True, False] and states[0].error is None
	assert states[1].powerboard_id == offline.id and states[1].outlets is None and "did not respond" in states[1].error
