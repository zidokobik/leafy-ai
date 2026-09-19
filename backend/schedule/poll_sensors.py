import logging
from datetime import datetime

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db_models.sensor_data import SensorData
from backend.dependencies.database_session import get_engine

logger = logging.getLogger(__name__)


def iso_datetime_to_timestamp_ms(iso_datetime: str) -> int:
	return int(datetime.fromisoformat(iso_datetime).timestamp() * 1000)


async def poll_sensors():
	"""
	Poll sensors readings and store the data in the database.
	"""

	url = "https://api.thingspeak.com/channels/3464601/feeds/last.json"
	logger.info("Polling ThingSpeak sensor feed from %s", url)

	async with httpx.AsyncClient() as client:
		try:
			response = await client.get(url)
			response.raise_for_status()
		except httpx.HTTPError:
			logger.exception("ThingSpeak sensor fetch failed")
			raise

		try:
			data = response.json()
		except ValueError:
			logger.exception("ThingSpeak response was not valid JSON")
			raise

		logger.info("Received ThingSpeak payload for sensor reading at %s", data.get("created_at"))

		# Store the data in the database
		sensor_data = SensorData(
			timestamp_ms=iso_datetime_to_timestamp_ms(data["created_at"]),
			water_ph=float(data["field1"]),
			ec_us_cm=float(data["field2"]),
			water_temp_c=float(data["field3"]),
			ambient_temp_c=float(data["field4"]),
			humidity_pct=float(data["field5"]),
			reservoir_level_cm=float(data["field6"]),
		)

	engine = get_engine()
	async with AsyncSession(engine, expire_on_commit=False) as session:
		session.add(sensor_data)
		try:
			await session.commit()
		except sa.exc.IntegrityError as e:
			# Ignore the expected duplicate primary-key race when the same sensor reading
			# is already present, but re-raise anything else as a real data issue.
			if 'duplicate key value violates unique constraint "sensor_data_pkey"' in str(e):
				logger.warning(
					"Skipping duplicate sensor_data row for timestamp_ms=%s",
					sensor_data.timestamp_ms,
				)
				return
			logger.exception("Failed to persist sensor_data for timestamp_ms=%s", sensor_data.timestamp_ms)
			raise
