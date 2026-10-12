from fastapi import APIRouter

from backend.router import alerts, auth, camera, chat, devices, notifications, proposals, schedules, sensors, users

router = APIRouter(prefix="/api/v1")

router.include_router(sensors.router)
router.include_router(camera.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(chat.router)
router.include_router(schedules.router)
router.include_router(devices.router)
router.include_router(devices.powerboards_router)
router.include_router(proposals.router)
router.include_router(alerts.router)
router.include_router(notifications.router)
