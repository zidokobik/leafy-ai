from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

MonitorRange = Literal["24H", "7D", "30D"]


class MonitoringHistoryPoint(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	id: UUID
	timestamp: datetime
	water_ph: float = Field(alias="waterPh")
	ec_us_cm: float = Field(alias="nutrientEcMicrosiemens")
	water_temp_c: float = Field(alias="waterTemperatureC")
	ambient_temp_c: float = Field(alias="temperatureC")
	humidity_pct: float = Field(alias="humidityPercent")
	reservoir_level_cm: float = Field(alias="reservoirLevelCm")
	irrigation_pump_on: bool = Field(alias="irrigationPumpOn")
	ec_target_us_cm: float = Field(alias="ecTargetMicrosiemens")


class MonitoringHistoryResponse(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	range: MonitorRange
	points: list[MonitoringHistoryPoint]
