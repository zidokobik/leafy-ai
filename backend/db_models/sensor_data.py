import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class SensorData(SQLModel, table=True):
	__tablename__ = "sensor_data"

	id: uuid.UUID = Field(primary_key=True)
	water_ph: float | None = None
	ec_us_cm: float | None = None
	water_temp_c: float | None = None
	ambient_temp_c: float | None = None
	humidity_pct: float | None = None
	reservoir_level_cm: float | None = None
	irrigation_pump_state: int | None = None
	ec_target_us_cm: float | None = None
	created_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
