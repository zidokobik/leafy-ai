import ai
from httpx2 import AsyncClient

# TODO: document about open implementation


@ai.tool
async def list_cameras() -> dict[int, list[int]]:
	"""
	Returns all cameras for each farm level.

	Each key in the dictionary represents a farm level, and the corresponding value is a list of camera IDs available at that level.
	"""
	# TODO: read from database instead of returning a hardcoded values
	return {1: [1, 2, 3], 2: [2]}


@ai.tool
async def get_camera_image(level: int, camera: int = 1) -> ai.messages.ContentOutput:
	"""
	Returns the latest image from the farm camera at the specified level.
	"""

	async with AsyncClient() as client:
		response = await client.get(
			f"https://deoscnkssyjenelneezs.supabase.co/storage/v1/object/public/images/level{level}_camera{camera}.jpg"
		)
		part = ai.file_part(response.content)
	return ai.content_output(f"Here is the image for level {level}, camera {camera}", part)
