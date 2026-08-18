from fastapi import FastAPI

import backend.router.camera
import backend.router.controller
import backend.router.water_sensor
import backend.settings

settings = backend.config.Settings()
app = FastAPI(root_path="/api")

app.include_router(backend.router.water_sensor.router)
app.include_router(backend.router.camera.router)
app.include_router(backend.router.controller.router)

# Serve the built frontend during production.
# During development, it is recommended to serve the frontend separately (`npm run dev`) to take advantage of live reloading and other Vite features.
if settings.ENVIRONMENT == "production":
	app.frontend("/", directory="frontend/dist")
