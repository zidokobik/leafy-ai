"""Stateful dashboard alerts: at most one active alert per alert_key, re-raises update in place."""

import re
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.alerts import Alert
from backend.schemas.alerts import AlertResolver, AlertSeverity, AlertStatusFilter

ALERT_KEY_PATTERN = re.compile(r"[a-z0-9_]{1,64}")
MAX_TITLE_LENGTH = 160
MAX_MESSAGE_LENGTH = 4000

# Critical first, then most recently raised.
_SEVERITY_ORDER = sa.case({"critical": 0, "warning": 1, "info": 2}, value=Alert.severity, else_=3)


class AlertNotFoundError(LookupError):
	pass


async def list_alerts(
	session: AsyncSession, status: AlertStatusFilter = "active", limit: int = 50, offset: int = 0
) -> list[Alert]:
	statement = select(Alert).order_by(_SEVERITY_ORDER, Alert.updated_at.desc()).limit(limit).offset(offset)
	if status != "all":
		statement = statement.where(Alert.status == status)
	return list((await session.execute(statement)).scalars().all())


async def raise_alert(
	session: AsyncSession,
	alert_key: str,
	severity: AlertSeverity,
	title: str,
	message: str,
	*,
	schedule_id: UUID | None = None,
) -> Alert:
	"""Create an active alert, or update the existing active alert with the same key.

	The update path bumps `occurrences` and `updated_at` so repeated raises (for
	example from scheduled runs) never stack duplicate rows.
	"""
	title = title.strip()
	message = message.strip()
	if not ALERT_KEY_PATTERN.fullmatch(alert_key):
		raise ValueError("alert_key must be 1-64 characters of lowercase snake_case ([a-z0-9_]).")
	if not 0 < len(title) <= MAX_TITLE_LENGTH:
		raise ValueError(f"title must be non-blank and at most {MAX_TITLE_LENGTH} characters.")
	if not 0 < len(message) <= MAX_MESSAGE_LENGTH:
		raise ValueError(f"message must be non-blank and at most {MAX_MESSAGE_LENGTH} characters.")

	statement = (
		insert(Alert)
		.values(
			alert_key=alert_key,
			severity=severity,
			title=title,
			message=message,
			status="active",
			occurrences=1,
			schedule_id=schedule_id,
		)
		.on_conflict_do_update(
			index_elements=["alert_key"],
			index_where=sa.text("status = 'active'"),
			set_={
				"severity": severity,
				"title": title,
				"message": message,
				"occurrences": Alert.occurrences + 1,
				"updated_at": sa.func.now(),
				"schedule_id": schedule_id,
				# A re-raise resurfaces a dismissed alert on the dashboard.
				"dismissed_at": None,
			},
		)
		.returning(Alert)
	)
	# populate_existing: apply RETURNING values even if the row is already in the identity map.
	result = await session.execute(statement, execution_options={"populate_existing": True})
	alert = result.scalars().one()
	await session.commit()
	return alert


async def dismiss_alert(session: AsyncSession, alert_id: UUID) -> Alert:
	"""Hide an active alert from the dashboard pin without resolving it. Idempotent."""
	alert = await session.get(Alert, alert_id)
	if alert is None:
		raise AlertNotFoundError("Alert not found.")
	if alert.status == "resolved" or alert.dismissed_at is not None:
		return alert
	alert.dismissed_at = datetime.now(UTC)
	session.add(alert)
	await session.commit()
	return alert


async def resolve_alert(session: AsyncSession, alert_id: UUID, resolved_by: AlertResolver) -> Alert:
	"""Mark an alert resolved. Resolving an already resolved alert is a no-op."""
	alert = await session.get(Alert, alert_id)
	if alert is None:
		raise AlertNotFoundError("Alert not found.")
	if alert.status == "resolved":
		return alert
	now = datetime.now(UTC)
	alert.status = "resolved"
	alert.resolved_at = now
	alert.resolved_by = resolved_by
	alert.updated_at = now
	session.add(alert)
	await session.commit()
	return alert
