from datetime import datetime

from sqlalchemy import case
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db_models.command_requests import CommandRequest

EXPIRABLE_STATUSES = ("pending_approval", "approved")


def effective_command(record: CommandRequest, now: datetime) -> CommandRequest:
	"""Read-only snapshot: never expire an operation that already started."""
	if record.status in EXPIRABLE_STATUSES and record.started_at is None and record.expires_at <= now:
		return record.model_copy(update={"status": "expired", "result_message": "Request expired before execution."})
	return record


def effective_status_expression(now: datetime):
	return case(
		(
			(CommandRequest.status.in_(EXPIRABLE_STATUSES))
			& (CommandRequest.started_at.is_(None))
			& (CommandRequest.expires_at <= now),
			"expired",
		),
		else_=CommandRequest.status,
	)


async def commit_snapshot(session: AsyncSession, record):
	"""Read generated values before commit; return an independent, loaded snapshot.

	No database read occurs after commit, even with expire_on_commit=True.
	Caller owns rollback if flush, refresh or commit raises.
	"""
	await session.flush()
	await session.refresh(record)
	snapshot = type(record).model_validate(record, from_attributes=True)
	await session.commit()
	return snapshot
