"""Self-hosted authentication: password hashing and JWT session cookies."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import Response
from pwdlib import PasswordHash

from backend.settings import Settings

_password_hash = PasswordHash.recommended()

JWT_ALGORITHM = "HS256"


class InvalidSessionTokenError(Exception):
	pass


def hash_password(password: str) -> str:
	return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
	return _password_hash.verify(password, password_hash)


def create_session_token(user_id: UUID, settings: Settings) -> str:
	now = datetime.now(UTC)
	payload = {
		"sub": str(user_id),
		"iat": now,
		"exp": now + timedelta(seconds=settings.SESSION_TTL_SECONDS),
	}
	return jwt.encode(payload, settings.JWT_SECRET_KEY.get_secret_value(), algorithm=JWT_ALGORITHM)


def decode_session_token(token: str, settings: Settings) -> UUID:
	try:
		payload = jwt.decode(token, settings.JWT_SECRET_KEY.get_secret_value(), algorithms=[JWT_ALGORITHM])
		return UUID(str(payload["sub"]))
	except (jwt.InvalidTokenError, KeyError, ValueError) as error:
		raise InvalidSessionTokenError from error


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
	response.set_cookie(
		key=settings.SESSION_COOKIE_NAME,
		value=token,
		max_age=settings.SESSION_TTL_SECONDS,
		httponly=True,
		samesite="lax",
		secure=settings.ENVIRONMENT == "production",
		path="/",
	)


def clear_session_cookie(response: Response, settings: Settings) -> None:
	response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
