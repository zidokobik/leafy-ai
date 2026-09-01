from typing import Any
from uuid import UUID

from httpx import HTTPError
from postgrest.exceptions import APIError

from backend.schemas.user import CurrentUserResponse
from backend.services.supabase import SupabaseConfiguration, get_supabase_admin_client


class UserProfileNotFoundError(Exception):
	pass


class UserProfileQueryError(Exception):
	pass


def get_user_profile(user_id: UUID, configuration: SupabaseConfiguration) -> CurrentUserResponse:
	client = get_supabase_admin_client(configuration.url, configuration.secret_key)

	try:
		user_result = (
			client.table("users")
			.select("user_id,email,first_name,last_name,created_at,updated_at,last_login_at")
			.eq("user_id", str(user_id))
			.limit(1)
			.execute()
		)
		if not user_result.data:
			raise UserProfileNotFoundError

		role_result = client.table("user_role").select("role_id").eq("user_id", str(user_id)).execute()
		role_ids = [row["role_id"] for row in role_result.data]
		roles = _get_role_names(client, role_ids)
	except UserProfileNotFoundError:
		raise
	except (APIError, HTTPError, KeyError, TypeError, ValueError) as error:
		raise UserProfileQueryError from error

	user = user_result.data[0]
	return CurrentUserResponse(
		id=user["user_id"],
		email=user["email"],
		first_name=user.get("first_name"),
		last_name=user.get("last_name"),
		roles=roles,
		created_at=user["created_at"],
		updated_at=user.get("updated_at"),
		last_login_at=user.get("last_login_at"),
	)


def _get_role_names(client: Any, role_ids: list[int]) -> list[str]:
	if not role_ids:
		return []

	role_result = client.table("roles").select("role_name").in_("role_id", role_ids).execute()
	return sorted(row["role_name"] for row in role_result.data if row.get("role_name"))
