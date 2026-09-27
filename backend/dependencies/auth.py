from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from backend.db_models.users import Users
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.user import AuthenticatedUser
from backend.services.auth import InvalidSessionTokenError, decode_session_token
from backend.settings import Settings, get_settings


def unauthorized(detail: str = "Invalid or expired session") -> HTTPException:
	return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def get_current_auth_user(
	request: Request,
	settings: Annotated[Settings, Depends(get_settings)],
	session: AsyncDatabaseSession,
) -> AuthenticatedUser:
	token = request.cookies.get(settings.SESSION_COOKIE_NAME)
	if token is None:
		raise unauthorized("Sign in is required")

	try:
		user_id: UUID = decode_session_token(token, settings)
	except InvalidSessionTokenError as error:
		raise unauthorized() from error

	if await session.get(Users, user_id) is None:
		raise unauthorized("Account no longer exists")
	return AuthenticatedUser(id=user_id)
