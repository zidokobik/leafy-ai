from datetime import UTC, datetime, timedelta
from typing import Any

from supabase import Client

from backend.schemas.monitoring import MonitoringHistoryPoint, MonitorRange

RANGE_DURATIONS = {"24H": timedelta(hours=24), "7D": timedelta(days=7), "30D": timedelta(days=30)}
PAGE_SIZE = 1000


def get_history(client: Client, monitor_range: MonitorRange) -> list[MonitoringHistoryPoint]:
	cutoff = datetime.now(UTC) - RANGE_DURATIONS[monitor_range]
	rows: list[dict[str, Any]] = []
	start = 0

	while True:
		response = (
			client.table("sensor_data")
			.select(
				"id,water_ph,ec_us_cm,water_temp_c,ambient_temp_c,humidity_pct,"
				"reservoir_level_cm,irrigation_pump_state,ec_target_us_cm,created_at"
			)
			.gte("created_at", cutoff.isoformat())
			.order("created_at")
			.range(start, start + PAGE_SIZE - 1)
			.execute()
		)
		page = response.data or []
		rows.extend(page)
		if len(page) < PAGE_SIZE:
			break
		start += PAGE_SIZE

	return [
		MonitoringHistoryPoint(
			id=row["id"],
			timestamp=row["created_at"],
			waterPh=row["water_ph"],
			nutrientEcMicrosiemens=row["ec_us_cm"],
			waterTemperatureC=row["water_temp_c"],
			temperatureC=row["ambient_temp_c"],
			humidityPercent=row["humidity_pct"],
			reservoirLevelCm=row["reservoir_level_cm"],
			irrigationPumpOn=bool(row["irrigation_pump_state"]),
			ecTargetMicrosiemens=row["ec_target_us_cm"],
		)
		for row in rows
	]
