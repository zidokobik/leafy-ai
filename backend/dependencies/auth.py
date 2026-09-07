from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from httpx import HTTPError
from supabase_auth.errors import AuthApiError, AuthError, AuthRetryableError, AuthUnknownError

from backend.schemas.user import AuthenticatedUser
from backend.services.supabase import get_supabase_auth_client, get_supabase_configuration
from backend.settings import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized(detail: str = "Invalid or expired access token") -> HTTPException:
	return HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail=detail,
		headers={"WWW-Authenticate": "Bearer"},
	)


def get_current_auth_user(
	credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
	settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
	if credentials is None:
		raise unauthorized("Bearer access token is required")

	configuration = get_supabase_configuration(settings)
	auth_client = get_supabase_auth_client(configuration.url, configuration.publishable_key)

	try:
		claims_response = auth_client.auth.get_claims(credentials.credentials)
	except (AuthRetryableError, AuthUnknownError, HTTPError) as error:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Unable to verify the access token",
		) from error
	except AuthApiError as error:
		if error.status >= 500:
			raise HTTPException(
				status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
				detail="Unable to verify the access token",
			) from error
		raise unauthorized() from error
	except (AuthError, KeyError, TypeError, ValueError) as error:
		raise unauthorized() from error

	if claims_response is None:
		raise unauthorized()

	claims = claims_response["claims"]
	expected_issuer = f"{configuration.url}/auth/v1"
	if claims.get("iss") != expected_issuer:
		raise unauthorized()

	try:
		user_id = UUID(str(claims["sub"]))
	except (KeyError, TypeError, ValueError) as error:
		raise unauthorized() from error

	email = claims.get("email")
	return AuthenticatedUser(id=user_id, email=email if isinstance(email, str) else None)
