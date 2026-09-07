from fastapi import APIRouter

from backend.router import camera, controller, history, monitoring, users, water_sensor

router = APIRouter(prefix="/api/v1")

router.include_router(water_sensor.router)
router.include_router(camera.router)
router.include_router(controller.router)
router.include_router(history.router)
router.include_router(monitoring.router)
router.include_router(users.router)
