import uuid

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class Powerboard(SQLModel, table=True):
	"""A Kasa power strip on the farm network, reached by IP address or hostname."""

	__tablename__ = "powerboards"

	id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	name: str
	host: str = Field(unique=True)


class Device(SQLModel, table=True):
	"""Equipment plugged into one outlet of a powerboard; outlet_num is 1-based."""

	__tablename__ = "devices"
	__table_args__ = (sa.UniqueConstraint("powerboard_id", "outlet_num", name="devices_powerboard_outlet_unique"),)

	id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
	name: str
	# fan | light | irrigation_pump | ec_doser | ph_doser (see backend/schemas/devices.py).
	device_type: str
	powerboard_id: uuid.UUID = Field(foreign_key="powerboards.id")
	outlet_num: int
