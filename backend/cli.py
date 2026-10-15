"""CLI for managing Leafy user accounts (internal app: sign-in only, no self-service signup)."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.db_models.users import Users
from backend.services.camera import CameraSyncConfig, sync_camera_images
from backend.services.harvest_readiness import BatchNotFoundError, record_harvest, record_move
from backend.services.plant_observations import insert_observations, read_observation_files
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


@app.command("sync-cameras")
def sync_cameras_command() -> None:
	"""Copy the latest camera images from the AWS's API into Supabase Storage now."""

	config = CameraSyncConfig.from_settings(get_settings())
	if config is None:
		typer.echo(
			"Set STUDENT_CLIENT_ID, STUDENT_USERNAME, STUDENT_PASSWORD, SUPABASE_URL and SUPABASE_SERVICE_KEY.",
			err=True,
		)
		raise typer.Exit(code=1)

	async def run() -> None:
		async with _make_session() as session:
			result = await sync_camera_images(session, config)
		for camera_id in result.updated:
			typer.echo(f"updated    {camera_id}")
		for camera_id in result.unchanged:
			typer.echo(f"unchanged  {camera_id}")
		for camera_id, error in result.failed.items():
			typer.echo(f"failed     {camera_id}: {error}", err=True)
		if result.failed:
			raise typer.Exit(code=1)

	asyncio.run(run())


@app.command("load-plant-observations")
def load_plant_observations_command(
	runs: str = typer.Option("cv/data/runs", help="Folder with one <camera>_<period>/observations.csv per map."),
) -> None:
	"""Load the CV's observations.csv files into plant_observations; rows already there are skipped."""

	runs_dir = Path(runs)
	if not runs_dir.is_dir():
		typer.echo(f"Folder '{runs}' not found.", err=True)
		raise typer.Exit(code=1)
	observations = read_observation_files(runs_dir)
	if not observations:
		typer.echo(f"No */observations.csv files with rows in '{runs}'.", err=True)
		raise typer.Exit(code=1)

	async def run() -> int:
		async with _make_session() as session:
			return await insert_observations(session, observations)

	inserted = asyncio.run(run())
	typer.echo(f"read {len(observations)} rows, inserted {inserted}, already there {len(observations) - inserted}")


@app.command("record-level2-move")
def record_level2_move_command(
	moved_at: Annotated[datetime, typer.Argument(help="Farm local time, e.g. 2026-10-15T16:00.")],
	note: str = typer.Option("", help="What moved, e.g. 'crowded channels from cameras 2 and 3'."),
) -> None:
	"""Record plants moved from Level 1 to Level 2; their harvest is due 7 days later."""

	async def run() -> None:
		async with _make_session() as session:
			batch = await record_move(session, moved_at, note)
		typer.echo(f"Recorded Level 2 batch {batch.id}, moved {batch.moved_at:%Y-%m-%d %H:%M}")

	asyncio.run(run())


@app.command("record-harvest")
def record_harvest_command(
	batch_id: int,
	harvested_at: Annotated[datetime, typer.Argument(help="Farm local time, e.g. 2026-10-15T17:00.")],
) -> None:
	"""Mark a Level 2 batch harvested."""

	async def run() -> None:
		async with _make_session() as session:
			try:
				batch = await record_harvest(session, batch_id, harvested_at)
			except (BatchNotFoundError, ValueError) as error:
				typer.echo(str(error), err=True)
				raise typer.Exit(code=1) from error
		typer.echo(f"Batch {batch.id} harvested {harvested_at:%Y-%m-%d %H:%M}")

	asyncio.run(run())


if __name__ == "__main__":
	app()
