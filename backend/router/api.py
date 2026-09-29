from fastapi import APIRouter

from backend.router import alerts, auth, camera, chat, safety, schedules, sensors, users

router = APIRouter(prefix="/api/v1")

router.include_router(sensors.router)
router.include_router(camera.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(chat.router)
router.include_router(schedules.router)
router.include_router(safety.router)
router.include_router(alerts.router)
