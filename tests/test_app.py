import pytest
from httpx import ASGITransport, AsyncClient

from main import app

# This is a "smoke test" to ensure that the FastAPI app is able to run, for CI/CD purpose.
# TODO: More comprehensive tests


@pytest.mark.asyncio
async def test_app():
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
	) as client:
		await client.get("/")
