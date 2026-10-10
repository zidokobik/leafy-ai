from uuid import UUID

import ai
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database_session import get_engine
from backend.schemas.notifications import EmailLogRead
from backend.services import emails


def send_email_tool(schedule_id: UUID | None = None):
	"""Bind trusted scheduler provenance outside the model-visible arguments."""

	@ai.tool
	async def send_email(subject: str, body: str) -> dict:
		"""Email the farm's admin recipients. This is your only outbound notification channel.

		Send one when a critical alert needs a human now (raise the dashboard alert
		first), or when a user or scheduled instruction explicitly asks for an
		emailed report. Admins read these away from the dashboard, so write a
		self-contained plain-text body: what happened, the key readings, and what to
		check or do. Do not email routine observations nobody asked for, and do not
		re-email an ongoing condition unless it materially worsened. Every attempt
		is logged on the Alerts page; a result with status "failed" includes the
		SMTP error and means nothing was delivered.
		"""
		async with AsyncSession(get_engine(), expire_on_commit=False) as session:
			log = await emails.send_email(session, subject, body, triggered_by="agent", schedule_id=schedule_id)
		return EmailLogRead.model_validate(log).model_dump(mode="json", by_alias=True)

	return send_email
