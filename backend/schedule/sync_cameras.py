import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database_session import get_engine
from backend.services.camera import CameraSyncConfig, sync_camera_images
from backend.settings import get_settings

logger = logging.getLogger(__name__)


async def sync_cameras():
	"""
	Copy the latest camera images from the AWS's API into Supabase Storage.
	"""

	config = CameraSyncConfig.from_settings(get_settings())
	if config is None:
		logger.warning("Skipping camera sync: STUDENT_* or SUPABASE_* settings are not configured")
		return

	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		result = await sync_camera_images(session, config)

	logger.info(
		"Camera sync finished: %d updated, %d unchanged, %d failed",
		len(result.updated),
		len(result.unchanged),
		len(result.failed),
	)
