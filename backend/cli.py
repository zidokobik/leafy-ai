"""CLI for managing Leafy user accounts (internal app: sign-in only, no self-service signup)."""

import asyncio
from uuid import UUID

import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.db_models.users import Users
from backend.services.users import create_user, get_user_by_email
from backend.settings import get_settings

app = typer.Typer(help="Manage Leafy user accounts.")


def _make_session() -> AsyncSession:
	settings = get_settings()
	engine = create_async_engine(settings.DATABASE_URI.get_secret_value())
	return AsyncSession(engine, expire_on_commit=False)


@app.command("create-user")
def create_user_command(
	email: str = typer.Option(..., prompt=True),
	password: str = typer.Option(..., prompt=True, confirmation_prompt=True, hide_input=True),
	first_name: str | None = typer.Option(None),
	last_name: str | None = typer.Option(None),
) -> None:
	"""Create a new user account."""

	async def run() -> None:
		async with _make_session() as session:
			if await get_user_by_email(session, email) is not None:
				typer.echo(f"A user with email '{email}' already exists.", err=True)
				raise typer.Exit(code=1)
			user = await create_user(session, email, password, first_name, last_name)
			typer.echo(f"Created user {user.email} ({user.user_id})")

	asyncio.run(run())


@app.command("list-users")
def list_users_command() -> None:
	"""List all user accounts."""

	async def run() -> None:
		async with _make_session() as session:
			result = await session.execute(select(Users).order_by(Users.email))
			for user in result.scalars():
				typer.echo(f"{user.user_id}  {user.email}  {user.first_name or ''} {user.last_name or ''}".rstrip())

	asyncio.run(run())


@app.command("delete-user")
def delete_user_command(user_id: UUID) -> None:
	"""Delete a user account by ID."""

	async def run() -> None:
		async with _make_session() as session:
			user = await session.get(Users, user_id)
			if user is None:
				typer.echo(f"No user found with id '{user_id}'.", err=True)
				raise typer.Exit(code=1)
			await session.delete(user)
			await session.commit()
			typer.echo(f"Deleted user {user.email} ({user.user_id})")

	asyncio.run(run())


if __name__ == "__main__":
	app()
