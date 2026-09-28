from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.schedules import AgentScheduledJobRead, AgentScheduledJobWrite
from backend.services import schedule as schedule_service

router = APIRouter(
	prefix="/schedules",
	tags=["schedules"],
	dependencies=[Depends(get_current_auth_user)],
)


@router.get("", response_model=list[AgentScheduledJobRead], description="List configured agent schedule jobs.")
async def read_scheduled_jobs(session: AsyncDatabaseSession) -> list[AgentScheduledJobRead]:
	jobs = [
		AgentScheduledJobRead(
			id=job.id,
			title=job.title,
			instruction=job.instruction,
			cron_expression=job.cron_expression,
			created_at=job.created_at,
			next_run=schedule_service.get_next_job_run(str(job.id)),
		)
		for job in await schedule_service.list_scheduled_jobs(session)
	]
	return jobs


@router.post("", response_model=AgentScheduledJobRead, status_code=status.HTTP_201_CREATED)
async def create_scheduled_job(
	payload: AgentScheduledJobWrite,
	session: AsyncDatabaseSession,
) -> AgentScheduledJobRead:
	job = await schedule_service.create_scheduled_job(
		session,
		payload.title,
		payload.instruction,
		payload.cron_expression,
	)
	return AgentScheduledJobRead.model_validate(job).model_copy(
		update={"next_run": schedule_service.get_next_job_run(str(job.id))}
	)


@router.patch("/{job_id}", response_model=AgentScheduledJobRead)
async def update_scheduled_job(
	job_id: UUID,
	payload: AgentScheduledJobWrite,
	session: AsyncDatabaseSession,
) -> AgentScheduledJobRead:
	job = await schedule_service.update_scheduled_job(
		session,
		job_id,
		payload.title,
		payload.instruction,
		payload.cron_expression,
	)
	if job is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled job not found")
	return AgentScheduledJobRead.model_validate(job).model_copy(
		update={"next_run": schedule_service.get_next_job_run(str(job.id))}
	)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_job(job_id: UUID, session: AsyncDatabaseSession) -> None:
	if not await schedule_service.delete_scheduled_job(session, job_id):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled job not found")
