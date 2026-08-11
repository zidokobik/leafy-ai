from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/water-sensor", tags=["water-sensor"])


class WaterSendorReadings(BaseModel):
	device: str
	ph: float
	ec: int
	ec_units: str
	ph_units: str
	ph_raw: str
	ec_raw: str = Field(
		...,
		example="1049,566,0.52,1.001",
	)
	ph_valid: bool
	ec_valid: bool
	ph_error: str | None
	ec_error: str | None
	ph_status: str
	ec_status: str
	ph_response_code: int
	ec_response_code: int
	measurement_duration_ms: int
	uptime_ms: int
	wifi_rssi_dbm: int
	ip: str
	hostname: str


@router.get(
	"/readings",
	description="""
	Retrieve the latest water sensor readings.
	Note: for now, this endpoint is currently a mock implementation and returns hardcoded values.
	""",
)
async def get_water_sensor_readings() -> WaterSendorReadings:
	# TODO: This is a mock response for water sensor readings.
	return WaterSendorReadings(
		device="WaterSensors",
		ph=8.034,
		ec=1049,
		ec_units="uS/cm",
		ph_units="pH",
		ph_raw="8.034",
		ec_raw="1049,566,0.52,1.001",
		ph_valid=True,
		ec_valid=True,
		ph_error=None,
		ec_error=None,
		ph_status="success",
		ec_status="success",
		ph_response_code=1,
		ec_response_code=1,
		measurement_duration_ms=1010,
		uptime_ms=78103065,
		wifi_rssi_dbm=-37,
		ip="192.168.1.100",
		hostname="WaterSensors.local",
	)


class WaterSensorHealth(BaseModel):
	device: str
	status: str
	wifi_connected: bool
	ph_i2c_detected: bool
	ec_i2c_detected: bool
	ip: str
	wifi_rssi_dbm: int
	uptime_ms: int


@router.get(
	"/health",
	description="""
	Retrieve the health status of the water sensor.
	Note: for now, this endpoint is currently a mock implementation and returns hardcoded values.
	""",
)
async def get_water_sensor_health() -> WaterSensorHealth:
	# TODO: This is a mock response for water sensor health status.
	return WaterSensorHealth(
		device="WaterSensors",
		status="ok",
		wifi_connected=True,
		ph_i2c_detected=True,
		ec_i2c_detected=True,
		ip="192.168.1.100",
		wifi_rssi_dbm=-33,
		uptime_ms=78974176,
	)
