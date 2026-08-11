from fastapi import FastAPI

import src.router.camera
import src.router.controller
import src.router.water_sensor

app = FastAPI()

app.include_router(src.router.water_sensor.router)
app.include_router(src.router.camera.router)
app.include_router(src.router.controller.router)
