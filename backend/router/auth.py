from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.user import CurrentUserResponse, LoginRequest
from backend.services.auth import clear_session_cookie, create_session_token, set_session_cookie
from backend.services.users import authenticate_user, get_user_profile
from backend.settings import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=CurrentUserResponse)
async def login(
	credentials: LoginRequest,
	response: Response,
	session: AsyncDatabaseSession,
	settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUserResponse:
	user = await authenticate_user(session, credentials.email, credentials.password)
	if user is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

	token = create_session_token(user.user_id, settings)
	set_session_cookie(response, token, settings)
	return await get_user_profile(session, user.user_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, settings: Annotated[Settings, Depends(get_settings)]) -> Response:
	# Returning a new Response would drop the cookie header set on the injected one.
	clear_session_cookie(response, settings)
	response.status_code = status.HTTP_204_NO_CONTENT
	return response
