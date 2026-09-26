from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.camera import CameraImage
from backend.services import camera as camera_service

router = APIRouter(prefix="/camera", tags=["camera"])


@router.get(
	"/latest",
	dependencies=[Depends(get_current_auth_user)],
	description="""
		The latest image for every camera, ordered by camera id. Images are copied hourly from the
		AWS's API into Supabase Storage, so `imageUrl` is a permanent public link.
	""",
)
async def read_latest_camera_images(session: AsyncDatabaseSession) -> list[CameraImage]:
	return await camera_service.list_cameras(session)


@router.get(
	"/raw/{level}/{camera}",
	description="""
			Retrieve the raw camera feed for a specific level and camera.
			Returns an image file representing the current view from the specified camera.
			Note: for now, this endpoint is currently a mock implementation and returns a static image.
			""",
)
def get_raw_camera_data(level: int, camera: int) -> FileResponse:
	# Use synchronous route `def` instead of async since the camera feed API (openCV + RTSP) is synchronous and blocking.
	# The synchronous routes are run automatically by FastAPI in a thread pool to avoid blocking asynchronous code.
	# Using `async def ` would block the event loop and cause performance issues.

	# TODO: currently this returns a static image for demonstration purposes.
	# In a real implementation, this function should fetch the actual camera feed using
	# RTSP protocol
	return FileResponse("sample-data/camera-images/level1_camera1.jpg")
