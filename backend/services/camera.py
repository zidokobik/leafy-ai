"""Camera images synced from the tutor's API into Supabase Storage.

The tutor's API only hands out presigned S3 links that expire within minutes, so storing those links
does not work. `sync_camera_images` logs in to Cognito, asks the API for fresh links, downloads each
image, re-uploads it to a public Supabase Storage bucket, and records the permanent link in `cameras`.

Everything here takes an `AsyncSession` plus plain arguments and returns schema objects, so the
same functions back the HTTP routes, the scheduler, and later the chat agent's tool calls.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.cameras import Cameras
from backend.schemas.camera import CameraImage, CameraSyncResult
from backend.settings import Settings

logger = logging.getLogger(__name__)

COGNITO_REGION = "ap-southeast-2"
LATEST_IMAGES_URL = "https://hrfhf8qlce.execute-api.ap-southeast-2.amazonaws.com/images/student/latest"
IMAGE_LINK_FIELDS = ("url", "image_url", "presigned_url", "imageUrl", "presignedUrl", "download_url")


@dataclass(frozen=True)
class CameraSyncConfig:
	student_client_id: str
	student_username: str
	student_password: str
	supabase_url: str
	supabase_service_key: str
	bucket: str

	@classmethod
	def from_settings(cls, settings: Settings) -> CameraSyncConfig | None:
		"""Returns None when any credential is missing, so callers can skip the sync."""
		if not (
			settings.STUDENT_CLIENT_ID
			and settings.STUDENT_USERNAME
			and settings.STUDENT_PASSWORD
			and settings.SUPABASE_URL
			and settings.SUPABASE_SERVICE_KEY
		):
			return None
		return cls(
			student_client_id=settings.STUDENT_CLIENT_ID,
			student_username=settings.STUDENT_USERNAME,
			student_password=settings.STUDENT_PASSWORD.get_secret_value(),
			supabase_url=settings.SUPABASE_URL.rstrip("/"),
			supabase_service_key=settings.SUPABASE_SERVICE_KEY.get_secret_value(),
			bucket=settings.CAMERA_BUCKET,
		)


async def list_cameras(session: AsyncSession) -> list[CameraImage]:
	"""The latest synced image for every camera, ordered by id."""
	result = await session.execute(select(Cameras).order_by(Cameras.id))
	return [
		CameraImage(id=row.id, label=row.label, image_url=row.image_url, captured_at=row.captured_at)
		for row in result.scalars()
	]


async def sync_camera_images(session: AsyncSession, config: CameraSyncConfig) -> CameraSyncResult:
	"""Copy every camera's latest image into Supabase Storage, skipping images that are already synced."""
	sync_result = CameraSyncResult(updated=[], unchanged=[], failed={})

	async with httpx.AsyncClient(timeout=30) as client:
		token = await _get_access_token(client, config)
		images = await _get_latest_images(client, token)
		logger.info("Tutor API returned %d camera images", len(images))

		for image in images:
			camera_id = str(image.get("camera_name"))
			try:
				if await _save_camera_image(session, client, config, image):
					sync_result.updated.append(camera_id)
				else:
					sync_result.unchanged.append(camera_id)
			except Exception as error:
				await session.rollback()
				logger.exception("Camera image sync failed for %s", camera_id)
				sync_result.failed[camera_id] = str(error)

	return sync_result


async def _get_access_token(client: httpx.AsyncClient, config: CameraSyncConfig) -> str:
	response = await client.post(
		f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/",
		headers={
			"Content-Type": "application/x-amz-json-1.1",
			"X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
		},
		json={
			"AuthFlow": "USER_PASSWORD_AUTH",
			"ClientId": config.student_client_id,
			"AuthParameters": {"USERNAME": config.student_username, "PASSWORD": config.student_password},
		},
	)
	body = response.json()
	if response.status_code != 200:
		raise RuntimeError(f"Cognito login failed: {body.get('message') or response.status_code}")
	if "AuthenticationResult" not in body:
		raise RuntimeError(f"Cognito login needs a challenge response: {body.get('ChallengeName')}")
	return body["AuthenticationResult"]["AccessToken"]


async def _get_latest_images(client: httpx.AsyncClient, token: str) -> list[dict[str, Any]]:
	response = await client.get(LATEST_IMAGES_URL, headers={"Authorization": f"Bearer {token}"})
	if response.status_code in (401, 403):
		response = await client.get(LATEST_IMAGES_URL, headers={"Authorization": token})
	if response.status_code != 200:
		raise RuntimeError(f"Tutor image API failed ({response.status_code}): {response.text}")
	return response.json()["images"]


async def _save_camera_image(
	session: AsyncSession,
	client: httpx.AsyncClient,
	config: CameraSyncConfig,
	image: dict[str, Any],
) -> bool:
	"""Returns False when the stored image already has this `captured_at`."""
	camera_id = str(image["camera_name"])
	captured_at = datetime.fromisoformat(image["captured_at"])
	presigned_url = next((image[field] for field in IMAGE_LINK_FIELDS if image.get(field)), None)
	if presigned_url is None:
		raise RuntimeError(f"No image link found. Fields are: {', '.join(image)}")

	camera = await session.get(Cameras, camera_id)
	if camera is not None and camera.image_url and camera.captured_at == captured_at:
		return False

	download = await client.get(presigned_url)
	download.raise_for_status()

	# One object per camera, overwritten each sync. The `?t=` query busts browser and CDN caches.
	object_path = f"{camera_id}.jpg"
	upload = await client.post(
		f"{config.supabase_url}/storage/v1/object/{config.bucket}/{object_path}",
		headers={
			"Authorization": f"Bearer {config.supabase_service_key}",
			"apikey": config.supabase_service_key,
			"Content-Type": download.headers.get("Content-Type", "image/jpeg"),
			"Cache-Control": "max-age=60",
			"x-upsert": "true",
		},
		content=download.content,
	)
	if upload.status_code != 200:
		raise RuntimeError(f"Supabase upload failed ({upload.status_code}): {upload.text}")

	public_url = f"{config.supabase_url}/storage/v1/object/public/{config.bucket}/{object_path}"
	if camera is None:
		camera = Cameras(id=camera_id, label=image.get("label") or camera_id)
		session.add(camera)
	elif image.get("label"):
		camera.label = image["label"]
	camera.image_url = f"{public_url}?t={int(captured_at.timestamp())}"
	camera.captured_at = captured_at
	await session.commit()

	logger.info("Synced camera image %s captured at %s", camera_id, captured_at.isoformat())
	return True
