from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.notifications import EmailLogRead, EmailRecipientCreate, EmailRecipientRead, EmailRecipientUpdate
from backend.services import emails

router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(get_current_auth_user)])


@router.get("/recipients", response_model=list[EmailRecipientRead], description="Recipients, oldest first.")
async def list_recipients(session: AsyncDatabaseSession):
	return await emails.list_recipients(session)


@router.post("/recipients", response_model=EmailRecipientRead, status_code=201)
async def add_recipient(payload: EmailRecipientCreate, session: AsyncDatabaseSession):
	try:
		return await emails.add_recipient(session, payload.email, payload.label)
	except ValueError as error:
		raise HTTPException(409, str(error)) from error


@router.patch("/recipients/{recipient_id}", response_model=EmailRecipientRead, description="Enable or disable.")
async def update_recipient(recipient_id: UUID, payload: EmailRecipientUpdate, session: AsyncDatabaseSession):
	try:
		return await emails.set_recipient_enabled(session, recipient_id, payload.enabled)
	except emails.RecipientNotFoundError as error:
		raise HTTPException(404, str(error)) from error


@router.delete("/recipients/{recipient_id}", status_code=204)
async def delete_recipient(recipient_id: UUID, session: AsyncDatabaseSession):
	try:
		await emails.delete_recipient(session, recipient_id)
	except emails.RecipientNotFoundError as error:
		raise HTTPException(404, str(error)) from error


@router.get("/emails", response_model=list[EmailLogRead], description="Email send log, most recent first.")
async def list_email_logs(
	session: AsyncDatabaseSession,
	limit: Annotated[int, Query(ge=1, le=100)] = 50,
	offset: Annotated[int, Query(ge=0)] = 0,
):
	return await emails.list_email_logs(session, limit, offset)


@router.post(
	"/emails/test",
	response_model=EmailLogRead,
	description="Send a test email to all enabled recipients and log the attempt.",
)
async def send_test_email(session: AsyncDatabaseSession):
	try:
		return await emails.send_test_email(session)
	except emails.EmailNotConfiguredError as error:
		raise HTTPException(503, str(error)) from error
	except ValueError as error:
		raise HTTPException(400, str(error)) from error
