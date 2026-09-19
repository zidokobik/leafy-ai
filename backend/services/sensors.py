"""Read access to `sensor_data`.

Everything here takes an `AsyncSession` plus plain arguments and returns schema objects, so the
same functions back the HTTP routes and, later, the chat agent's tool calls.
"""

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.sensor_data import SensorData
from backend.schemas.sensors import SensorHistory, SensorRange, SensorReading

MEASUREMENTS = (
	"water_ph",
	"ec_us_cm",
	"water_temp_c",
	"ambient_temp_c",
	"humidity_pct",
	"reservoir_level_cm",
)

RANGE_WINDOWS: dict[SensorRange, timedelta] = {
	"24h": timedelta(hours=24),
	"7d": timedelta(days=7),
	"30d": timedelta(days=30),
}

# Sensors are polled every 30 seconds, so a raw 30 day range is ~86k rows. Averaging each range
# into buckets keeps a response around 200 points, which is enough resolution for a chart and
# small enough to fit in an agent's context.
RANGE_BUCKETS: dict[SensorRange, timedelta] = {
	"24h": timedelta(minutes=5),
	"7d": timedelta(hours=1),
	"30d": timedelta(hours=4),
}


def _to_ms(moment: datetime) -> int:
	return int(moment.timestamp() * 1000)


def _to_datetime(timestamp_ms: int) -> datetime:
	return datetime.fromtimestamp(timestamp_ms / 1000, UTC)


async def get_history(
	session: AsyncSession,
	sensor_range: SensorRange,
	now: datetime | None = None,
) -> SensorHistory:
	"""Average the readings of `sensor_range` into fixed buckets, oldest first."""

	end = now or datetime.now(UTC)
	start = end - RANGE_WINDOWS[sensor_range]
	bucket = RANGE_BUCKETS[sensor_range]
	bucket_ms = int(bucket.total_seconds() * 1000)

	bucket_start = (SensorData.timestamp_ms // bucket_ms) * bucket_ms
	statement = (
		select(
			bucket_start.label("bucket_start"),
			*(sa.func.avg(getattr(SensorData, name)).label(name) for name in MEASUREMENTS),
		)
		.where(SensorData.timestamp_ms >= _to_ms(start), SensorData.timestamp_ms <= _to_ms(end))
		.group_by(bucket_start)
		.order_by(bucket_start)
	)
	rows = (await session.execute(statement)).all()

	return SensorHistory(
		range=sensor_range,
		start=start,
		end=end,
		bucket_seconds=int(bucket.total_seconds()),
		readings=[
			SensorReading(
				timestamp=_to_datetime(row.bucket_start),
				# avg() returns Decimal, which Pydantic would reject for a float field.
				**{name: _as_float(getattr(row, name)) for name in MEASUREMENTS},
			)
			for row in rows
		],
	)


async def get_latest_reading(session: AsyncSession) -> SensorReading | None:
	"""The newest raw sample, unaveraged. Returns None when the table is empty."""

	statement = select(SensorData).order_by(sa.desc(SensorData.timestamp_ms)).limit(1)
	row = (await session.execute(statement)).scalars().first()
	if row is None:
		return None

	return SensorReading(
		timestamp=_to_datetime(row.timestamp_ms),
		**{name: getattr(row, name) for name in MEASUREMENTS},
	)


def _as_float(value: object) -> float | None:
	return None if value is None else float(value)  # type: ignore[arg-type]
