from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from backend.schemas.plant_readiness import ObservationKind, PlantStatus


class PlantObservation(SQLModel, table=True):
	__tablename__ = "plant_observations"
	__table_args__ = (
		# One row per frame x hole x model version; the loader skips rows that are already there.
		sa.UniqueConstraint("image_id", "hole_id", "model_version", name="plant_observations_unique"),
	)

	id: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger, sa.Identity(always=True), primary_key=True))
	image_id: str = Field(sa_type=sa.Text)
	model_version: str = Field(sa_type=sa.Text)
	camera_id: str = Field(sa_type=sa.Text)
	# Farm local time from the frame's file name; the timezone is not confirmed.
	captured_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=False), nullable=False))
	level: int = Field(sa_type=sa.SmallInteger)
	period: str = Field(sa_type=sa.Text)
	hole_id: str = Field(sa_type=sa.Text)
	kind: ObservationKind = Field(sa_type=sa.Text)
	row: int | None = Field(default=None, sa_type=sa.SmallInteger)
	col: int | None = Field(default=None, sa_type=sa.SmallInteger)
	in_frame: float | None = Field(default=None, sa_type=sa.REAL)
	occupied: bool
	# For a zone: how closed the canopy is.
	coverage: float = Field(sa_type=sa.REAL)
	boundary_contact: float | None = Field(default=None, sa_type=sa.REAL)
	contact_along: float | None = Field(default=None, sa_type=sa.REAL)
	contact_across: float | None = Field(default=None, sa_type=sa.REAL)
	plant_area_px: int | None = None
	status: PlantStatus = Field(sa_type=sa.Text)
	confirmed_frames: int = Field(sa_type=sa.SmallInteger)
	flags: list[str] = Field(
		default_factory=list, sa_column=sa.Column(sa.ARRAY(sa.Text), nullable=False, server_default="{}")
	)
