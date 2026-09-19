from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

import backend.router.api
import backend.settings
from backend.schedule.poll_sensors import poll_sensors

settings = backend.settings.get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
	scheduler = AsyncIOScheduler()
	scheduler.add_job(poll_sensors, "interval", seconds=30)
	scheduler.start()

	yield

	scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

app.include_router(backend.router.api.router)


class SinglePageApp(StaticFiles):
	"""Serves the built dashboard, falling back to index.html so client-side routes survive a reload."""

	async def get_response(self, path: str, scope: Scope):
		try:
			return await super().get_response(path, scope)
		except StarletteHTTPException as error:
			if error.status_code != 404:
				raise
			return await super().get_response("index.html", scope)


# Serve the built frontend during production.
# During development, it is recommended to serve the frontend separately (`npm run dev`) to take advantage of live reloading and other Vite features.
if settings.ENVIRONMENT == "production":
	app.mount("/", SinglePageApp(directory=Path("frontend/dist"), html=True), name="frontend")
