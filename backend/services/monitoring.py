from datetime import UTC, datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.sensor_data import SensorData
from backend.schemas.monitoring import MonitoringHistoryPoint, MonitoringLatestResponse, MonitorRange

RANGE_DURATIONS = {
	"24H": timedelta(hours=24),
	"7D": timedelta(days=7),
	"30D": timedelta(days=30),
}


def _complete_reading_query():
	columns = (
		SensorData.water_ph,
		SensorData.ec_us_cm,
		SensorData.water_temp_c,
		SensorData.ambient_temp_c,
		SensorData.humidity_pct,
		SensorData.reservoir_level_cm,
		SensorData.irrigation_pump_state,
		SensorData.ec_target_us_cm,
	)
	return select(SensorData).where(*(column.is_not(None) for column in columns))


def _to_history_point(row: SensorData) -> MonitoringHistoryPoint:
	return MonitoringHistoryPoint(
		id=row.id,
		timestamp=row.created_at,
		waterPh=row.water_ph,
		nutrientEcMicrosiemens=row.ec_us_cm,
		waterTemperatureC=row.water_temp_c,
		temperatureC=row.ambient_temp_c,
		humidityPercent=row.humidity_pct,
		reservoirLevelCm=row.reservoir_level_cm,
		irrigationPumpOn=bool(row.irrigation_pump_state),
		ecTargetMicrosiemens=row.ec_target_us_cm,
	)


async def get_history(session: AsyncSession, monitor_range: MonitorRange) -> list[MonitoringHistoryPoint]:
	cutoff = datetime.now(UTC) - RANGE_DURATIONS[monitor_range]
	statement = _complete_reading_query().where(SensorData.created_at >= cutoff).order_by(SensorData.created_at)
	result = await session.execute(statement)
	return [_to_history_point(row) for row in result.scalars()]


async def get_latest(session: AsyncSession) -> MonitoringLatestResponse | None:
	statement = _complete_reading_query().order_by(desc(SensorData.created_at)).limit(1)
	result = await session.execute(statement)
	row = result.scalars().first()
	if row is None:
		return None

	checks = [
		5.8 <= row.water_ph <= 6.5,
		22 <= row.ambient_temp_c <= 26,
		60 <= row.humidity_pct <= 75,
		row.ec_us_cm <= row.ec_target_us_cm,
	]
	score = round(sum(checks) / len(checks) * 100)
	return MonitoringLatestResponse(
		healthScore=score,
		status="healthy" if score >= 75 else "attention",
		temperatureC=row.ambient_temp_c,
		humidityPercent=row.humidity_pct,
		waterPh=row.water_ph,
		nutrientEcMicrosiemens=row.ec_us_cm,
		updatedAt=row.created_at,
	)
