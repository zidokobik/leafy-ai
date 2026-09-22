from contextlib import asynccontextmanager
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession

from backend.db_models.agent_scheduled_job import AgentScheduledJob
from backend.services.schedule import list_scheduled_jobs
from backend.settings import get_settings

from .agent_job import execute_agent_scheduled_job
from .poll_sensors import poll_sensors

SCHEDULER = AsyncIOScheduler()
SENSOR_POLL_JOB_ID = "sensor-poll"


def _agent_job_id(job_id: UUID) -> str:
	return f"agent-job-{job_id}"


async def add_agent_scheduled_job_to_scheduler(job: AgentScheduledJob) -> None:
	trigger = CronTrigger.from_crontab(job.cron_expression)
	SCHEDULER.add_job(
		execute_agent_scheduled_job,
		trigger=trigger,
		id=_agent_job_id(job.id),
		name=job.title,
		kwargs={"job": job},
		replace_existing=True,
		max_instances=1
	)


async def remove_agent_scheduled_job_from_scheduler(job_id: UUID) -> None:
	scheduler_job_id = _agent_job_id(job_id)
	if SCHEDULER.get_job(scheduler_job_id) is not None:
		SCHEDULER.remove_job(scheduler_job_id)


@asynccontextmanager
async def run_scheduler():
	SCHEDULER.add_job(poll_sensors, "interval", seconds=30, id=SENSOR_POLL_JOB_ID, replace_existing=True)

	settings = get_settings()
	engine = create_async_engine(settings.DATABASE_URI.get_secret_value())
	async with AsyncSession(engine) as session:
		scheduled_jobs = await list_scheduled_jobs(session)

	for job in scheduled_jobs:
		await add_agent_scheduled_job_to_scheduler(job)

	SCHEDULER.start()
	try:
		yield
	finally:
		SCHEDULER.shutdown(True)
