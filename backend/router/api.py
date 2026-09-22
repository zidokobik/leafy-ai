from fastapi import APIRouter

from backend.router import auth, camera, chat, schedules, sensors, users

router = APIRouter(prefix="/api/v1")

router.include_router(sensors.router)
router.include_router(camera.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(chat.router)
router.include_router(schedules.router)
