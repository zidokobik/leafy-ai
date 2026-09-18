from fastapi import FastAPI

import backend.router.api
import backend.settings

settings = backend.settings.get_settings()
app = FastAPI()

app.include_router(backend.router.api.router)

# Serve the built frontend during production.
# During development, it is recommended to serve the frontend separately (`npm run dev`) to take advantage of live reloading and other Vite features.
if settings.ENVIRONMENT == "production":
	app.frontend("/", directory="frontend/dist")
