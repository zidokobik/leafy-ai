"""
This module contains the router for controlling the farm hardware
such as pH doser, EC doser, irrigation pump, fan and lights.

For the moment, this is a mock implementation that returns static values for the hardware status.
See https://github.com/fergaletto/PowerStripControl for reference.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/controller", tags=["controller"])


class HardwareStatus(BaseModel):
	name: str
	on: bool


@router.get("/fan", description="Get current fan status")
async def get_fan_status():
	on = True  # TODO: Replace with actual logic to get fan status
	return HardwareStatus(name="fan", on=on)


@router.put("/fan", description="Turn fan on or off")
async def set_fan_status(on: bool):
	# TODO: Replace with actual logic to set fan status
	return HardwareStatus(name="fan", on=on)


@router.get("/lights", description="Get current lights status")
async def get_lights_status():
	on = True  # TODO: Replace with actual logic to get lights status
	return HardwareStatus(name="lights", on=on)


@router.put("/lights", description="Turn lights on or off")
async def set_lights_status(on: bool):
	# TODO: Replace with actual logic to set lights status
	return HardwareStatus(name="lights", on=on)


@router.get("/pump", description="Get current irrigation pump status")
async def get_pump_status():
	on = True  # TODO: Replace with actual logic to get pump status
	return HardwareStatus(name="pump", on=on)


@router.put("/pump", description="Turn irrigation pump on or off")
async def set_pump_status(on: bool):
	# TODO: Replace with actual logic to set pump status
	return HardwareStatus(name="pump", on=on)


@router.get("/ph_doser", description="Get current pH doser status")
async def get_ph_doser_status():
	on = True  # TODO: Replace with actual logic to get pH doser status
	return HardwareStatus(name="ph_doser", on=on)


@router.put("/ph_doser", description="Turn pH doser on or off")
async def set_ph_doser_status(on: bool):
	# TODO: Replace with actual logic to set pH doser status
	return HardwareStatus(name="ph_doser", on=on)


@router.get("/ec_doser", description="Get current EC doser status")
async def get_ec_doser_status():
	on = True  # TODO: Replace with actual logic to get EC doser status
	return HardwareStatus(name="ec_doser", on=on)


@router.put("/ec_doser", description="Turn EC doser on or off")
async def set_ec_doser_status(on: bool):
	# TODO: Replace with actual logic to set EC doser status
	return HardwareStatus(name="ec_doser", on=on)
