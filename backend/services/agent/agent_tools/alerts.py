from uuid import UUID

import ai
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db_models.alerts import Alert
from backend.dependencies.database_session import get_engine
from backend.schemas.alerts import AlertRead, AlertSeverity
from backend.services import alerts as alert_service


def _dump(alert: Alert) -> dict:
	return AlertRead.model_validate(alert).model_dump(mode="json", by_alias=True)


@ai.tool
async def list_alerts(include_resolved: bool = False) -> dict:
	"""List dashboard alerts, critical first. Check this before raising or resolving alerts.

	Alerts stay active until explicitly resolved by you or a user. A non-null
	dismissedAt only hides the alert from the dashboard pin; reuse an existing
	active alertKey to update that alert in place and resurface it.
	"""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		active = await alert_service.list_alerts(session, "active", limit=50)
		resolved = await alert_service.list_alerts(session, "resolved", limit=20) if include_resolved else []
	result = {"active": [_dump(alert) for alert in active]}
	if include_resolved:
		result["recentlyResolved"] = [_dump(alert) for alert in resolved]
	return result


def raise_alert_tool(schedule_id: UUID | None = None):
	"""Bind trusted scheduler provenance outside the model-visible arguments."""

	@ai.tool
	async def raise_alert(alert_key: str, severity: AlertSeverity, title: str, message: str) -> dict:
		"""Raise a dashboard alert, or update the active alert that already has this alert_key.

		alert_key is a stable snake_case condition id such as water_ph_high — reuse the
		exact key of an existing active alert for the same condition (see list_alerts);
		never append timestamps or counters. Re-raising updates the alert in place,
		increments occurrences instead of duplicating, and resurfaces it if a user had
		dismissed it. severity critical means a human must act now; warning means
		developing problem; info is routine. Alerts notify no external systems.
		Resolve with resolve_alert once the condition clears.
		"""
		async with AsyncSession(get_engine(), expire_on_commit=False) as session:
			alert = await alert_service.raise_alert(
				session, alert_key, severity, title, message, schedule_id=schedule_id
			)
		payload = _dump(alert)
		payload["created"] = alert.occurrences == 1
		return payload

	return raise_alert


@ai.tool
async def resolve_alert(alert_id: UUID) -> dict:
	"""Resolve an active dashboard alert once tool evidence shows its condition cleared.

	Get alert_id from list_alerts. Resolving an already resolved alert is a no-op.
	"""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		alert = await alert_service.resolve_alert(session, alert_id, resolved_by="agent")
	return _dump(alert)
