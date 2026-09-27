import pytest
from httpx import ASGITransport, AsyncClient

from main import app

# TODO: Test authorized user, using credentials from environment variables

# --- Root & Smoke Test ---
@pytest.mark.asyncio
async def test_app():
	"""Smoke test to ensure the FastAPI app starts and responds to the base URL."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.get("/")
	# Accepts 200 (production) or 404 (if frontend root is not mounted in test mode)
	assert response.status_code in [200, 404]


# --- Camera Test ---
@pytest.mark.asyncio
async def test_get_raw_camera_data():
	"""Check that the raw camera image feed endpoint returns a successful response."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.get("/api/v1/camera/raw/1/1")
	assert response.status_code == 200


# --- Authentication & Protected Routes (Expect 401 Unauthorized) ---
@pytest.mark.asyncio
async def test_login_unauthorized():
	"""Ensure login fails with a 401 Unauthorized error when bad credentials are provided."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.post(
			"/api/v1/auth/login", json={"email": "wrong@example.com", "password": "wrongpassword"}
		)
	assert response.status_code == 401


@pytest.mark.asyncio
async def test_sensors_history_unauthorized():
	"""Ensure unauthenticated users cannot access historical sensor data."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.get("/api/v1/sensors/history")
	assert response.status_code == 401


@pytest.mark.asyncio
async def test_latest_camera_images_unauthorized():
	"""Ensure unauthenticated users cannot list the latest camera images."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.get("/api/v1/camera/latest")
	assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_user_unauthorized():
	"""Ensure unauthenticated users cannot view their user profile page."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.get("/api/v1/users/me")
	assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_unauthorized():
	"""Ensure unauthenticated users cannot access the AI chat agent endpoint."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.post("/api/v1/chat", json={"messages": []})
	assert response.status_code == 401
