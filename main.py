from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

import backend.router.api
import backend.settings
from backend.schedule.poll_sensors import poll_sensors

settings = backend.settings.get_settings()


async def lifespan(app: FastAPI):
	scheduler = AsyncIOScheduler()
	scheduler.add_job(poll_sensors, "interval", seconds=30)
	scheduler.start()

	yield


app = FastAPI(lifespan=lifespan)

app.include_router(backend.router.api.router)

# Serve the built frontend during production.
# During development, it is recommended to serve the frontend separately (`npm run dev`) to take advantage of live reloading and other Vite features.
if settings.ENVIRONMENT == "production":
	app.frontend("/", directory="frontend/dist")
