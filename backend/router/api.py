from fastapi import APIRouter

from backend.router import auth, camera, chat, controller, sensors, users, water_sensor

router = APIRouter(prefix="/api/v1")

router.include_router(sensors.router)
router.include_router(water_sensor.router)
router.include_router(camera.router)
router.include_router(controller.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(chat.router)
