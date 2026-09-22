from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.agent_scheduled_job import AgentScheduledJob


async def list_scheduled_jobs(session: AsyncSession) -> list[AgentScheduledJob]:
	query = select(AgentScheduledJob).order_by(sa.desc(AgentScheduledJob.created_at))
	result = await session.execute(query)
	return result.scalars().all()


async def create_scheduled_job(
	session: AsyncSession,
	title: str,
	instruction: str,
	cron_expression: str,
) -> AgentScheduledJob:
	"""Persist and immediately register a scheduled agent run."""

	from backend.schedule import add_agent_scheduled_job_to_scheduler

	job = AgentScheduledJob(
		title=title,
		instruction=instruction,
		cron_expression=cron_expression,
	)
	session.add(job)

	try:
		await session.flush()
		await add_agent_scheduled_job_to_scheduler(job)
		await session.commit()
	except Exception:
		await session.rollback()
		if job.id is not None:
			from backend.schedule import remove_agent_scheduled_job_from_scheduler

			await remove_agent_scheduled_job_from_scheduler(job.id)
		raise

	return job


async def update_scheduled_job(
	session: AsyncSession,
	job_id: UUID,
	title: str,
	instruction: str,
	cron_expression: str,
) -> AgentScheduledJob | None:
	"""Update a schedule and replace its active scheduler registration."""

	job = await session.get(AgentScheduledJob, job_id)
	if job is None:
		return None

	from backend.schedule import add_agent_scheduled_job_to_scheduler

	previous_job = AgentScheduledJob(
		id=job.id,
		title=job.title,
		instruction=job.instruction,
		cron_expression=job.cron_expression,
	)
	job.title = title
	job.instruction = instruction
	job.cron_expression = cron_expression

	try:
		await session.flush()
		await add_agent_scheduled_job_to_scheduler(job)
		await session.commit()
	except Exception:
		await session.rollback()
		await add_agent_scheduled_job_to_scheduler(previous_job)
		raise

	return job


async def delete_scheduled_job(session: AsyncSession, job_id: UUID) -> bool:
	"""Remove a persisted agent run and its in-memory scheduler entry."""

	job = await session.get(AgentScheduledJob, job_id)
	if job is None:
		return False

	from backend.schedule import add_agent_scheduled_job_to_scheduler, remove_agent_scheduled_job_from_scheduler

	await remove_agent_scheduled_job_from_scheduler(job.id)
	try:
		await session.delete(job)
		await session.commit()
	except Exception:
		await session.rollback()
		await add_agent_scheduled_job_to_scheduler(job)
		raise

	return True
