from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.devices import DeviceRead, DeviceWrite, PowerboardRead, PowerboardStateRead, PowerboardWrite
from backend.schemas.user import AuthenticatedUser
from backend.services import devices as device_service
from backend.services import outlets
from backend.services import proposals as proposal_service

router = APIRouter(prefix="/devices", tags=["devices"], dependencies=[Depends(get_current_auth_user)])
powerboards_router = APIRouter(prefix="/powerboards", tags=["devices"], dependencies=[Depends(get_current_auth_user)])

CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_auth_user)]


def _http_error(error: Exception) -> HTTPException:
	if isinstance(error, device_service.DeviceConflictError):
		return HTTPException(409, str(error))
	return HTTPException(404, str(error))


DeviceErrors = (
	device_service.DeviceNotFoundError,
	device_service.PowerboardNotFoundError,
	device_service.DeviceConflictError,
)


@powerboards_router.get("", response_model=list[PowerboardRead], description="Powerboards ordered by name.")
async def list_powerboards(session: AsyncDatabaseSession):
	return await device_service.list_powerboards(session)


@powerboards_router.get(
	"/states",
	response_model=list[PowerboardStateRead],
	description="Live outlet states read from every powerboard. Unreachable boards report an error instead.",
)
async def read_powerboard_states(session: AsyncDatabaseSession):
	return await device_service.read_powerboard_states(session)


@powerboards_router.post("", response_model=PowerboardRead, status_code=201)
async def create_powerboard(payload: PowerboardWrite, session: AsyncDatabaseSession):
	try:
		return await device_service.create_powerboard(session, payload.name, payload.host)
	except DeviceErrors as error:
		raise _http_error(error) from error


@powerboards_router.put("/{powerboard_id}", response_model=PowerboardRead)
async def update_powerboard(powerboard_id: UUID, payload: PowerboardWrite, session: AsyncDatabaseSession):
	try:
		return await device_service.update_powerboard(session, powerboard_id, payload.name, payload.host)
	except DeviceErrors as error:
		raise _http_error(error) from error


@powerboards_router.delete(
	"/{powerboard_id}", status_code=204, description="Delete a powerboard. Returns 409 while devices still use it."
)
async def delete_powerboard(powerboard_id: UUID, session: AsyncDatabaseSession):
	try:
		await device_service.delete_powerboard(session, powerboard_id)
	except DeviceErrors as error:
		raise _http_error(error) from error


@router.get("", response_model=list[DeviceRead], description="Devices ordered by powerboard name, then outlet.")
async def list_devices(session: AsyncDatabaseSession):
	return await device_service.list_devices(session)


@router.post("", response_model=DeviceRead, status_code=201)
async def create_device(payload: DeviceWrite, session: AsyncDatabaseSession):
	try:
		return await device_service.create_device(
			session, payload.name, payload.device_type, payload.powerboard_id, payload.outlet_num
		)
	except DeviceErrors as error:
		raise _http_error(error) from error


@router.put("/{device_id}", response_model=DeviceRead)
async def update_device(device_id: UUID, payload: DeviceWrite, session: AsyncDatabaseSession):
	try:
		return await device_service.update_device(
			session, device_id, payload.name, payload.device_type, payload.powerboard_id, payload.outlet_num
		)
	except DeviceErrors as error:
		raise _http_error(error) from error


@router.delete(
	"/{device_id}",
	status_code=204,
	description="Delete a device and reject its pending proposal. A run in progress still switches off on time.",
)
async def delete_device(device_id: UUID, session: AsyncDatabaseSession):
	try:
		await device_service.delete_device(session, device_id)
	except DeviceErrors as error:
		raise _http_error(error) from error


async def _switch(session: AsyncDatabaseSession, device_id: UUID, user: AuthenticatedUser, *, on: bool) -> None:
	try:
		await proposal_service.switch_device(session, device_id, on=on, user_id=user.id)
	except device_service.DeviceNotFoundError as error:
		raise HTTPException(404, str(error)) from error
	except outlets.PowerboardError as error:
		raise HTTPException(502, str(error)) from error


@router.post(
	"/{device_id}/turn-on",
	status_code=204,
	description="Switch the device on now; it stays on until switched off. Returns 502 if the powerboard fails.",
)
async def turn_on_device(device_id: UUID, session: AsyncDatabaseSession, user: CurrentUser):
	await _switch(session, device_id, user, on=True)


@router.post(
	"/{device_id}/turn-off",
	status_code=204,
	description="Switch the device off now, stopping its run in progress. Returns 502 if the powerboard fails.",
)
async def turn_off_device(device_id: UUID, session: AsyncDatabaseSession, user: CurrentUser):
	await _switch(session, device_id, user, on=False)
