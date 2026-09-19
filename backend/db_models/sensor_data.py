from time import time

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class SensorData(SQLModel, table=True):
	__tablename__ = "sensor_data"

	timestamp_ms: int = Field(
		default=int(time() * 1000),
		sa_column=sa.Column(sa.BigInteger, primary_key=True),
	)
	water_ph: float | None = None
	ec_us_cm: float | None = None
	water_temp_c: float | None = None
	ambient_temp_c: float | None = None
	humidity_pct: float | None = None
	reservoir_level_cm: float | None = None
