from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

SensorRange = Literal["24h", "7d", "30d"]


class SensorReading(BaseModel):
	"""One sensor sample, or the average of a bucket of samples when it comes from a history range."""

	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	timestamp: datetime
	water_ph: float | None = None
	ec_us_cm: float | None = None
	water_temp_c: float | None = None
	ambient_temp_c: float | None = None
	humidity_pct: float | None = None
	reservoir_level_cm: float | None = None


class SensorHistory(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	range: SensorRange
	start: datetime
	end: datetime
	bucket_seconds: int
	readings: list[SensorReading]
