from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies.auth import get_current_auth_user
from backend.schemas.user import AuthenticatedUser, CurrentUserResponse
from backend.services.supabase import get_supabase_configuration
from backend.services.users import UserProfileNotFoundError, UserProfileQueryError, get_user_profile
from backend.settings import Settings, get_settings

router = APIRouter(prefix="/users", tags=["users"])


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
