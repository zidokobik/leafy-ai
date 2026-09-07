from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from httpx import HTTPError
from supabase_auth.errors import AuthApiError, AuthError

from backend.dependencies.auth import get_current_auth_user
from backend.schemas.user import AuthenticatedUser, CurrentUserResponse, UpdateUserProfile
from backend.services.supabase import get_supabase_configuration
from backend.services.users import (
	UserProfileNotFoundError,
	UserProfileQueryError,
	delete_user_account,
	get_user_profile,
	update_user_profile,
)
from backend.settings import Settings, get_settings

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=CurrentUserResponse)
def update_current_user(
	update: UpdateUserProfile,
	current_user: Annotated[AuthenticatedUser, Depends(get_current_auth_user)],
	settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUserResponse:
	try:
		return update_user_profile(current_user.id, update, get_supabase_configuration(settings))
	except UserProfileNotFoundError as error:
		raise HTTPException(404, "User profile was not found") from error
	except UserProfileQueryError as error:
		raise HTTPException(503, "Unable to update the user profile") from error


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
	current_user: Annotated[AuthenticatedUser, Depends(get_current_auth_user)],
	settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
	try:
		delete_user_account(current_user.id, get_supabase_configuration(settings))
	except AuthApiError as error:
		if error.status != 404:
			raise HTTPException(
				503, "Unable to delete the account. Please retry or contact your administrator."
			) from error
	except (AuthError, HTTPError) as error:
		raise HTTPException(503, "Unable to delete the account. Please try again.") from error
	return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(
	current_user: Annotated[AuthenticatedUser, Depends(get_current_auth_user)],
	settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUserResponse:
	configuration = get_supabase_configuration(settings)

	try:
		return get_user_profile(current_user.id, configuration)
	except UserProfileNotFoundError as error:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="User profile was not found",
		) from error
	except UserProfileQueryError as error:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Unable to load the user profile",
		) from error
