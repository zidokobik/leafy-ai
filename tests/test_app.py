import os
import sys
from pathlib import Path

# --- Auto-fix working directory and python path ---
# This ensures Python can find the main backend modules correctly 
# no matter where we run pytest from in our terminal.
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
os.chdir(project_root)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Fix database URI settings for tests dynamically to use an in-memory SQLite DB
# This keeps tests safe and self-contained without needing a real database file.
import backend.settings
settings = backend.settings.get_settings()
if not settings.DATABASE_URI or settings.DATABASE_URI.get_secret_value() == "":
    from pydantic import SecretStr
    settings.DATABASE_URI = SecretStr("sqlite+aiosqlite:///:memory:")
# ---------------------------------------------------------------------

import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from unittest.mock import patch


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


# --- Water Sensor Tests (Mocked Endpoints) ---
@pytest.mark.asyncio
async def test_get_water_sensor_readings():
	"""Check that the water sensor readings endpoint returns correct mock data structure."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.get("/api/v1/water-sensor/readings")
	assert response.status_code == 200
	data = response.json()
	assert data["device"] == "WaterSensors"
	assert "ph" in data


@pytest.mark.asyncio
async def test_get_water_sensor_health():
	"""Check that the water sensor health status endpoint responds successfully."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.get("/api/v1/water-sensor/health")
	assert response.status_code == 200
	assert response.json()["status"] == "ok"


# --- Controller Tests ---
@pytest.mark.asyncio
async def test_get_fan_status():
	"""Verify that we can successfully fetch the current status of the farm fan."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.get("/api/v1/controller/fan")
	assert response.status_code == 200
	data = response.json()
	assert data["name"] == "fan"


@pytest.mark.asyncio
async def test_set_fan_status():
	"""Verify that we can toggle or update the farm fan status correctly."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.put("/api/v1/controller/fan?on=false")
	assert response.status_code == 200
	assert response.json()["on"] is False


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
@patch("backend.router.auth.authenticate_user", return_value=None)
async def test_login_unauthorized(mock_auth):
	"""Ensure login fails with a 401 Unauthorized error when bad credentials are provided."""
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		response = await client.post(
			"/api/v1/auth/login", 
			json={"email": "wrong@example.com", "password": "wrongpassword"}
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
