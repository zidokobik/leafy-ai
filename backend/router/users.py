from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.user import AuthenticatedUser, CurrentUserResponse, UpdateUserPassword, UpdateUserProfile
from backend.services.users import (
	UserProfileNotFoundError,
	delete_user_account,
	get_user_profile,
	update_user_password,
	update_user_profile,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=CurrentUserResponse)
async def update_current_user(
	update: UpdateUserProfile,
	current_user: Annotated[AuthenticatedUser, Depends(get_current_auth_user)],
	session: AsyncDatabaseSession,
) -> CurrentUserResponse:
	try:
		return await update_user_profile(session, current_user.id, update)
	except UserProfileNotFoundError as error:
		raise HTTPException(404, "User profile was not found") from error


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_current_user_password(
	update: UpdateUserPassword,
	current_user: Annotated[AuthenticatedUser, Depends(get_current_auth_user)],
	session: AsyncDatabaseSession,
) -> Response:
	try:
		await update_user_password(session, current_user.id, update.new_password)
	except UserProfileNotFoundError as error:
		raise HTTPException(404, "User profile was not found") from error
	return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
	current_user: Annotated[AuthenticatedUser, Depends(get_current_auth_user)],
	session: AsyncDatabaseSession,
) -> Response:
	try:
		await delete_user_account(session, current_user.id)
	except UserProfileNotFoundError as error:
		raise HTTPException(404, "User profile was not found") from error
	return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(
	current_user: Annotated[AuthenticatedUser, Depends(get_current_auth_user)],
	session: AsyncDatabaseSession,
) -> CurrentUserResponse:
	try:
		return await get_user_profile(session, current_user.id)
	except UserProfileNotFoundError as error:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="User profile was not found",
		) from error
