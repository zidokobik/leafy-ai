"""Admin notification emails over SMTP. Credentials come from .env; recipients and send logs live in the database."""

import logging
from email.message import EmailMessage
from email.utils import formataddr
from uuid import UUID

import aiosmtplib
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.email_notifications import EmailLog, EmailRecipient
from backend.schemas.notifications import EmailTrigger
from backend.settings import Settings, get_settings

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 30
MAX_SUBJECT_LENGTH = 200
MAX_BODY_LENGTH = 10_000


class EmailNotConfiguredError(RuntimeError):
	pass


class RecipientNotFoundError(LookupError):
	pass


def smtp_configured(settings: Settings) -> bool:
	return bool(settings.SMTP_HOST and settings.SMTP_USERNAME)


def _require_configured(settings: Settings) -> None:
	if not smtp_configured(settings):
		raise EmailNotConfiguredError("SMTP is not configured; set SMTP_HOST and SMTP_USERNAME in .env.")


def _validated(field: str, value: str, max_length: int) -> str:
	value = value.strip()
	if not 0 < len(value) <= max_length:
		raise ValueError(f"{field} must be non-blank and at most {max_length} characters.")
	return value


async def list_recipients(session: AsyncSession, enabled_only: bool = False) -> list[EmailRecipient]:
	statement = select(EmailRecipient).order_by(EmailRecipient.created_at)
	if enabled_only:
		statement = statement.where(EmailRecipient.enabled)
	return list((await session.execute(statement)).scalars().all())


async def add_recipient(session: AsyncSession, email: str, label: str | None = None) -> EmailRecipient:
	label = label.strip() if label else None
	recipient = EmailRecipient(email=email.strip().lower(), label=label or None)
	session.add(recipient)
	try:
		await session.commit()
	except IntegrityError as error:
		await session.rollback()
		raise ValueError("This email address is already a recipient.") from error
	return recipient


async def set_recipient_enabled(session: AsyncSession, recipient_id: UUID, enabled: bool) -> EmailRecipient:
	recipient = await session.get(EmailRecipient, recipient_id)
	if recipient is None:
		raise RecipientNotFoundError("Recipient not found.")
	recipient.enabled = enabled
	session.add(recipient)
	await session.commit()
	return recipient


async def delete_recipient(session: AsyncSession, recipient_id: UUID) -> None:
	recipient = await session.get(EmailRecipient, recipient_id)
	if recipient is None:
		raise RecipientNotFoundError("Recipient not found.")
	await session.delete(recipient)
	await session.commit()


async def list_email_logs(session: AsyncSession, limit: int = 50, offset: int = 0) -> list[EmailLog]:
	statement = select(EmailLog).order_by(EmailLog.created_at.desc()).limit(limit).offset(offset)
	return list((await session.execute(statement)).scalars().all())


async def send_email(
	session: AsyncSession,
	subject: str,
	body: str,
	*,
	triggered_by: EmailTrigger,
	schedule_id: UUID | None = None,
) -> EmailLog:
	"""Email every enabled recipient, logging the attempt whether it is delivered or fails."""
	settings = get_settings()
	_require_configured(settings)
	subject = _validated("subject", subject, MAX_SUBJECT_LENGTH)
	body = _validated("body", body, MAX_BODY_LENGTH)
	recipients = await list_recipients(session, enabled_only=True)
	if not recipients:
		raise ValueError("No enabled email recipients are configured on the Alerts page.")
	return await _send_and_log(
		session,
		settings,
		[recipient.email for recipient in recipients],
		subject=subject,
		body=body,
		schedule_id=schedule_id,
		triggered_by=triggered_by,
	)


async def send_test_email(session: AsyncSession) -> EmailLog:
	"""Send a configuration test email to every enabled recipient."""
	body = "This is a test email from the Leafy dashboard. Your SMTP configuration and recipient list work."
	return await send_email(session, "[Leafy] Test email", body, triggered_by="user")


async def _send_and_log(
	session: AsyncSession,
	settings: Settings,
	recipients: list[str],
	*,
	subject: str,
	body: str,
	schedule_id: UUID | None = None,
	triggered_by: EmailTrigger,
) -> EmailLog:
	message = EmailMessage()
	message["From"] = formataddr(("Leafy AI", settings.SMTP_USERNAME))
	message["To"] = ", ".join(recipients)
	message["Subject"] = subject
	message.set_content(body)
	password = settings.SMTP_PASSWORD.get_secret_value() if settings.SMTP_PASSWORD else None
	status, error = "sent", None
	try:
		await aiosmtplib.send(
			message,
			hostname=settings.SMTP_HOST,
			port=settings.SMTP_PORT,
			username=settings.SMTP_USERNAME,
			password=password or None,
			use_tls=settings.SMTP_USE_TLS,
			timeout=SMTP_TIMEOUT_SECONDS,
		)
	except (aiosmtplib.SMTPException, OSError) as exc:
		status = "failed"
		error = f"{type(exc).__name__}: {exc}"
		logger.warning("Email send failed (%s): %s", subject, error)
	log = EmailLog(
		recipients=recipients,
		subject=subject,
		status=status,
		error=error,
		schedule_id=schedule_id,
		triggered_by=triggered_by,
	)
	session.add(log)
	await session.commit()
	return log
