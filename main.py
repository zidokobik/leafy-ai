from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

import src.router.camera
import src.router.chat
import src.router.controller
import src.router.water_sensor


app = FastAPI(
	description="""
	NOTE: ALL DATA IS MOCKED AND NOT REAL.
	"""
)

app.include_router(src.router.water_sensor.router)
app.include_router(src.router.camera.router)
app.include_router(src.router.controller.router)
app.include_router(src.router.chat.router, prefix="/api")

frontend_dist_dir = Path(__file__).parent / "chatbot-prototype" / "dist"
app.mount(
	"/",
	StaticFiles(directory=frontend_dist_dir, html=True, check_dir=False),
	name="frontend",
)
