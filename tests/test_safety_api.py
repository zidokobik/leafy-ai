from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.db_models.command_requests import CommandRequest
from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import _async_database_session
from backend.router.safety import router
from backend.schemas.user import AuthenticatedUser
from backend.services import safety, safety_records
from backend.settings import Settings, get_settings


@pytest.fixture
def app():
	app = FastAPI()
	app.include_router(router, prefix="/api/v1")
	app.dependency_overrides[get_settings] = lambda: Settings(
		_env_file=None,
		AI_GATEWAY_API_KEY="test",
		AI_MODEL="test",
		DATABASE_URI="postgresql://unused",
		JWT_SECRET_KEY="test-secret-not-for-production",
	)
	app.dependency_overrides[_async_database_session] = lambda: object()
	return app


@pytest.mark.asyncio
@pytest.mark.parametrize(
	"method,path",
	[
		("GET", "/safety-rules"),
		("POST", "/safety-rules"),
		("GET", f"/safety-rules/{uuid4()}"),
		("PUT", f"/safety-rules/{uuid4()}"),
		("DELETE", f"/safety-rules/{uuid4()}"),
		("GET", "/ai-decisions"),
		("POST", "/ai-decisions"),
		("GET", f"/ai-decisions/{uuid4()}"),
		("GET", "/command-requests"),
		("POST", "/command-requests"),
		("GET", f"/command-requests/{uuid4()}"),
		("POST", f"/command-requests/{uuid4()}/review"),
	],
)
async def test_all_routes_require_login(app, method, path):
	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		assert (await client.request(method, "/api/v1" + path)).status_code == 401


@pytest.mark.asyncio
async def test_review_identity_and_payload(app, monkeypatch):
	user_id = uuid4()
	app.dependency_overrides[get_current_auth_user] = lambda: AuthenticatedUser(id=user_id)
	record = CommandRequest(
		device_id=uuid4(),
		duration_seconds=30,
		reason="Fan",
		status="approved",
		expires_at=datetime.now(UTC) + timedelta(minutes=10),
	)
	mock = AsyncMock(return_value=record)
	monkeypatch.setattr(safety, "review_command_request", mock)
	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		path = f"/api/v1/command-requests/{record.request_id}/review"
		response = await client.post(path, json={"action": "approve"})
		assert response.status_code == 200
		assert response.json()["requestId"] == str(record.request_id)
		assert mock.call_args.args[2] == user_id
		assert (await client.post(path, json={"action": "approve", "reviewedBy": str(uuid4())})).status_code == 422
		mock.side_effect = safety.SafetyConflictError("Already reviewed")
		assert (await client.post(path, json={"action": "reject"})).status_code == 409


@pytest.mark.asyncio
async def test_listing_and_not_found(app, monkeypatch):
	app.dependency_overrides[get_current_auth_user] = lambda: AuthenticatedUser(id=uuid4())
	mock = AsyncMock(return_value=[])
	monkeypatch.setattr(safety_records, "list_commands", mock)
	monkeypatch.setattr(safety_records, "get_record", AsyncMock(side_effect=safety.SafetyNotFoundError("Missing")))
	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		assert (await client.get("/api/v1/command-requests?status=blocked&limit=10&offset=2")).status_code == 200
		assert mock.call_args.args[3:] == ("blocked", 10, 2)
		assert (await client.get("/api/v1/command-requests?limit=101")).status_code == 422
		assert (await client.get("/api/v1/command-requests?status=invalid")).status_code == 422
		assert (await client.get(f"/api/v1/command-requests/{uuid4()}")).status_code == 404
