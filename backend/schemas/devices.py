from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

DeviceType = Literal["fan", "light", "irrigation_pump", "ec_doser", "ph_doser"]

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# An IP address or hostname only: python-kasa adds the protocol and port itself.
Host = Annotated[
	str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255, pattern=r"^[A-Za-z0-9.-]+$")
]


class PowerboardWrite(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

	name: Name
	host: Host


class PowerboardRead(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

	id: UUID
	name: str
	host: str


class PowerboardStateRead(BaseModel):
	"""Live outlet states read from the powerboard; `outlets` is null when it could not be reached."""

	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	powerboard_id: UUID
	outlets: list[bool] | None = None
	error: str | None = None


class DeviceWrite(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

	name: Name
	device_type: DeviceType
	powerboard_id: UUID
	outlet_num: int = Field(ge=1, le=64, description="1-based outlet position on the powerboard.")


class DeviceRead(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

	id: UUID
	name: str
	device_type: DeviceType
	powerboard_id: UUID
	outlet_num: int
