"""Powerboards (Kasa power strips) and the devices plugged into their outlets."""

import asyncio
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.device_proposals import DeviceProposal
from backend.db_models.devices import Device, Powerboard
from backend.schemas.devices import DeviceType, PowerboardStateRead
from backend.services import outlets


class DeviceNotFoundError(LookupError):
	pass


class PowerboardNotFoundError(LookupError):
	pass


class DeviceConflictError(ValueError):
	pass


async def _commit(session: AsyncSession, conflict_message: str) -> None:
	try:
		await session.commit()
	except IntegrityError as error:
		await session.rollback()
		raise DeviceConflictError(conflict_message) from error


async def _get_powerboard(session: AsyncSession, powerboard_id: UUID) -> Powerboard:
	powerboard = await session.get(Powerboard, powerboard_id)
	if powerboard is None:
		raise PowerboardNotFoundError("Powerboard not found.")
	return powerboard


async def get_device(session: AsyncSession, device_id: UUID) -> Device:
	device = await session.get(Device, device_id)
	if device is None:
		raise DeviceNotFoundError("Device not found.")
	return device


async def list_powerboards(session: AsyncSession) -> list[Powerboard]:
	return list((await session.execute(select(Powerboard).order_by(Powerboard.name))).scalars().all())


async def create_powerboard(session: AsyncSession, name: str, host: str) -> Powerboard:
	powerboard = Powerboard(name=name, host=host)
	session.add(powerboard)
	await _commit(session, f"Another powerboard already uses the host {host}.")
	return powerboard


async def update_powerboard(session: AsyncSession, powerboard_id: UUID, name: str, host: str) -> Powerboard:
	powerboard = await _get_powerboard(session, powerboard_id)
	powerboard.name = name
	powerboard.host = host
	session.add(powerboard)
	await _commit(session, f"Another powerboard already uses the host {host}.")
	return powerboard


async def delete_powerboard(session: AsyncSession, powerboard_id: UUID) -> None:
	powerboard = await _get_powerboard(session, powerboard_id)
	plugged_in = await session.scalar(
		select(sa.func.count()).select_from(Device).where(Device.powerboard_id == powerboard_id)
	)
	if plugged_in:
		raise DeviceConflictError(f"{plugged_in} device(s) use this powerboard; move or delete them first.")
	await session.delete(powerboard)
	await _commit(session, "Devices were added to this powerboard; move or delete them first.")


async def read_powerboard_states(session: AsyncSession) -> list[PowerboardStateRead]:
	"""Read every powerboard's outlets concurrently; an unreachable board reports an error instead."""
	powerboards = await list_powerboards(session)

	async def read(powerboard: Powerboard) -> PowerboardStateRead:
		try:
			return PowerboardStateRead(powerboard_id=powerboard.id, outlets=await outlets.read_outlets(powerboard.host))
		except outlets.PowerboardError as error:
			return PowerboardStateRead(powerboard_id=powerboard.id, error=str(error))

	return list(await asyncio.gather(*(read(powerboard) for powerboard in powerboards)))


async def list_devices(session: AsyncSession) -> list[Device]:
	statement = (
		select(Device)
		.join(Powerboard, Powerboard.id == Device.powerboard_id)
		.order_by(Powerboard.name, Device.outlet_num)
	)
	return list((await session.execute(statement)).scalars().all())


async def create_device(
	session: AsyncSession, name: str, device_type: DeviceType, powerboard_id: UUID, outlet_num: int
) -> Device:
	await _get_powerboard(session, powerboard_id)
	device = Device(name=name, device_type=device_type, powerboard_id=powerboard_id, outlet_num=outlet_num)
	session.add(device)
	await _commit(session, f"Outlet {outlet_num} on this powerboard is already assigned to another device.")
	return device


async def update_device(
	session: AsyncSession, device_id: UUID, name: str, device_type: DeviceType, powerboard_id: UUID, outlet_num: int
) -> Device:
	"""Edit a device. A run in progress keeps switching the outlet it started on."""
	device = await get_device(session, device_id)
	await _get_powerboard(session, powerboard_id)
	device.name = name
	device.device_type = device_type
	device.powerboard_id = powerboard_id
	device.outlet_num = outlet_num
	session.add(device)
	await _commit(session, f"Outlet {outlet_num} on this powerboard is already assigned to another device.")
	return device


async def delete_device(session: AsyncSession, device_id: UUID) -> None:
	"""Delete a device and reject its pending proposal. A run in progress still switches off on time."""
	device = await get_device(session, device_id)
	await session.execute(
		sa.update(DeviceProposal)
		.where(DeviceProposal.device_id == device_id, DeviceProposal.status == "pending")
		.values(status="rejected", reviewed_at=sa.func.now(), result_message="The device was deleted before review.")
		.execution_options(synchronize_session=False)
	)
	await session.delete(device)
	await session.commit()
