from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CameraImage(BaseModel):
	"""The latest synced image for one camera. `imageUrl` and `capturedAt` are null until the first sync."""

	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	id: str
	label: str
	image_url: str | None = None
	captured_at: datetime | None = None


class CameraSyncResult(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	updated: list[str]
	unchanged: list[str]
	failed: dict[str, str]
