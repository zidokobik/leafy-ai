"""Read access to `sensor_data`.

Everything here takes an `AsyncSession` plus plain arguments and returns schema objects, so the
same functions back the HTTP routes and, later, the chat agent's tool calls.
"""

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.sensor_data import SensorData
from backend.schemas.sensors import SensorHistory, SensorReading

MEASUREMENTS = (
	"water_ph",
	"ec_us_cm",
	"water_temp_c",
	"ambient_temp_c",
	"humidity_pct",
	"reservoir_level_cm",
)

# Sensors are polled every 30 seconds. Select the smallest standard bucket that keeps an interval
# to roughly 200 chart points, avoiding an unbounded payload for arbitrary date selections.
MAX_HISTORY_BUCKETS = 200
BUCKET_OPTIONS = (
	timedelta(minutes=1),
	timedelta(minutes=5),
	timedelta(minutes=15),
	timedelta(minutes=30),
	timedelta(hours=1),
	timedelta(hours=2),
	timedelta(hours=4),
	timedelta(hours=8),
	timedelta(hours=12),
	timedelta(days=1),
)


def _to_ms(moment: datetime) -> int:
	return int(moment.timestamp() * 1000)


def _to_datetime(timestamp_ms: int) -> datetime:
	return datetime.fromtimestamp(timestamp_ms / 1000, UTC)


def _select_bucket(before: datetime, end: datetime) -> timedelta:
	minimum_seconds = (end - before).total_seconds() / MAX_HISTORY_BUCKETS
	return next(
		(bucket for bucket in BUCKET_OPTIONS if bucket.total_seconds() >= minimum_seconds),
		BUCKET_OPTIONS[-1],
	)


async def get_history(
	session: AsyncSession,
	before: datetime,
	end: datetime,
) -> SensorHistory:
	"""Average the inclusive [`before`, `end`] interval into buckets, oldest first."""

	if before >= end:
		raise ValueError("before must be earlier than end")

	bucket = _select_bucket(before, end)
	bucket_ms = int(bucket.total_seconds() * 1000)

	bucket_start = (SensorData.timestamp_ms // bucket_ms) * bucket_ms
	statement = (
		select(
			bucket_start.label("bucket_start"),
			*(sa.func.avg(getattr(SensorData, name)).label(name) for name in MEASUREMENTS),
		)
		.where(SensorData.timestamp_ms >= _to_ms(before), SensorData.timestamp_ms <= _to_ms(end))
		.group_by(bucket_start)
		.order_by(bucket_start)
	)
	rows = (await session.execute(statement)).all()

	return SensorHistory(
		before=before,
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
