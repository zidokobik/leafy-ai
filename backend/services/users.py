from datetime import UTC, datetime
from uuid import UUID

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.users import Users
from backend.schemas.user import CurrentUserResponse, UpdateUserProfile
from backend.services.auth import hash_password, verify_password


class UserProfileNotFoundError(Exception):
	pass


async def get_user_by_email(session: AsyncSession, email: str) -> Users | None:
	result = await session.execute(select(Users).where(Users.email == email))
	return result.scalars().first()


async def authenticate_user(session: AsyncSession, email: str, password: str) -> Users | None:
	user = await get_user_by_email(session, email)
	if user is None:
		return None
	if not await run_in_threadpool(verify_password, password, user.password_hash):
		return None
	user.last_login_at = datetime.now(UTC)
	session.add(user)
	await session.commit()
	await session.refresh(user)
	return user


async def create_user(
	session: AsyncSession,
	email: str,
	password: str,
	first_name: str | None = None,
	last_name: str | None = None,
) -> Users:
	password_hash = await run_in_threadpool(hash_password, password)
	user = Users(
		email=email,
		password_hash=password_hash,
		first_name=first_name,
		last_name=last_name,
	)
	session.add(user)
	await session.commit()
	await session.refresh(user)
	return user


async def _get_user_or_raise(session: AsyncSession, user_id: UUID) -> Users:
	user = await session.get(Users, user_id)
	if user is None:
		raise UserProfileNotFoundError
	return user


def _to_response(user: Users) -> CurrentUserResponse:
	return CurrentUserResponse(
		id=user.user_id,
		email=user.email,
		first_name=user.first_name,
		last_name=user.last_name,
		created_at=user.created_at,
		updated_at=user.updated_at,
		last_login_at=user.last_login_at,
	)


async def get_user_profile(session: AsyncSession, user_id: UUID) -> CurrentUserResponse:
	user = await _get_user_or_raise(session, user_id)
	return _to_response(user)


async def update_user_profile(session: AsyncSession, user_id: UUID, update: UpdateUserProfile) -> CurrentUserResponse:
	user = await _get_user_or_raise(session, user_id)
	values = update.model_dump(exclude_unset=True)
	if values:
		for key, value in values.items():
			setattr(user, key, value)
		user.updated_at = datetime.now(UTC)
		session.add(user)
		await session.commit()
		await session.refresh(user)
	return _to_response(user)


async def update_user_password(session: AsyncSession, user_id: UUID, new_password: str) -> None:
	user = await _get_user_or_raise(session, user_id)
	user.password_hash = await run_in_threadpool(hash_password, new_password)
	user.updated_at = datetime.now(UTC)
	session.add(user)
	await session.commit()


async def delete_user_account(session: AsyncSession, user_id: UUID) -> None:
	user = await _get_user_or_raise(session, user_id)
	await session.delete(user)
	await session.commit()
