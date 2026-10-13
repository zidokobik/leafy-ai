"""Level 2 harvest timing: a batch is due 7 days after it moved up from Level 1 (the owner's rule), not a CV measure."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.level2_batches import Level2Batch
from backend.schemas.harvest_readiness import BatchHarvest, HarvestReadiness, HarvestStatus
from backend.settings import get_settings

HARVEST_AFTER = timedelta(days=7)
WARN_BEFORE = timedelta(days=1)

MESSAGES: dict[HarvestStatus, str] = {
	HarvestStatus.GROWING: "Growing on Level 2: nothing to do yet",
	HarvestStatus.HARVEST_TOMORROW: "Harvest due tomorrow: plan the harvest",
	HarvestStatus.HARVEST_DUE: "Harvest due: check the plants and harvest today",
	HarvestStatus.HARVESTED: "Harvested",
}
NOTHING_ON_LEVEL2 = "Nothing growing on Level 2"

LIMITATIONS = (
	"Harvest timing is a date rule, 7 days after the plants moved to Level 2 (the owner's rule; the 30 Sep batch "
	"was harvested on 7 Oct), not a camera measurement: the grower checks the plants before harvesting. Moves and "
	"harvests are known only when they are recorded; the archived camera frames end on 8 Oct 2026."
)


class BatchNotFoundError(LookupError):
	pass


def farm_now() -> datetime:
	"""Return the current farm local time without a timezone, the clock the batch times use."""
	return datetime.now(ZoneInfo(get_settings().FARM_TIMEZONE)).replace(tzinfo=None)


def harvest_status(batch: Level2Batch, as_of: datetime) -> HarvestStatus:
	"""Return where the batch is in its harvest window at `as_of`."""
	if batch.harvested_at is not None and batch.harvested_at <= as_of:
		return HarvestStatus.HARVESTED
	due_at = batch.moved_at + HARVEST_AFTER
	if as_of >= due_at:
		return HarvestStatus.HARVEST_DUE
	if as_of >= due_at - WARN_BEFORE:
		return HarvestStatus.HARVEST_TOMORROW
	return HarvestStatus.GROWING


def to_batch_harvest(batch: Level2Batch, as_of: datetime) -> BatchHarvest:
	"""Return the harvest view of one batch at `as_of`."""
	status = harvest_status(batch, as_of)
	end = batch.harvested_at if status == HarvestStatus.HARVESTED else as_of
	return BatchHarvest(
		batch_id=batch.id,
		moved_at=batch.moved_at,
		due_at=batch.moved_at + HARVEST_AFTER,
		harvested_at=batch.harvested_at if status == HarvestStatus.HARVESTED else None,
		days_on_level2=round((end - batch.moved_at) / timedelta(days=1), 1),
		status=status,
		message=MESSAGES[status],
		note=batch.note,
	)


def summarise(batches: list[BatchHarvest]) -> str:
	"""Return e.g. "1 batch due for harvest", "Next harvest due 15 Oct 16:00", or "Nothing growing on Level 2"."""
	due = sum(batch.status == HarvestStatus.HARVEST_DUE for batch in batches)
	tomorrow = sum(batch.status == HarvestStatus.HARVEST_TOMORROW for batch in batches)
	parts = [
		f"{count} batch{'es' if count > 1 else ''} {label}"
		for count, label in ((due, "due for harvest"), (tomorrow, "due tomorrow"))
		if count
	]
	if parts:
		return ", ".join(parts)
	growing = [batch.due_at for batch in batches if batch.status == HarvestStatus.GROWING]
	return f"Next harvest due {min(growing):%d %b %H:%M}" if growing else NOTHING_ON_LEVEL2


async def get_harvest_readiness(session: AsyncSession, as_of: datetime | None = None) -> HarvestReadiness:
	"""Return every batch moved to Level 2 at or before `as_of` (None = now, farm time), newest first.

	A timezone on `as_of` is dropped, not converted: batch times are farm local time.
	"""
	as_of = farm_now() if as_of is None else as_of.replace(tzinfo=None)
	statement = select(Level2Batch).where(Level2Batch.moved_at <= as_of).order_by(Level2Batch.moved_at.desc())
	batches = [to_batch_harvest(batch, as_of) for batch in (await session.execute(statement)).scalars()]
	return HarvestReadiness(as_of=as_of, batches=batches, summary=summarise(batches), limitations=LIMITATIONS)


async def record_move(session: AsyncSession, moved_at: datetime, note: str = "") -> Level2Batch:
	"""Record plants moved from Level 1 to Level 2 (farm local time) and return the new batch."""
	batch = Level2Batch(moved_at=moved_at.replace(tzinfo=None), note=note.strip())
	session.add(batch)
	await session.commit()
	return batch


async def record_harvest(session: AsyncSession, batch_id: int, harvested_at: datetime) -> Level2Batch:
	"""Mark a batch harvested (farm local time) and return it."""
	batch = await session.get(Level2Batch, batch_id)
	if batch is None:
		raise BatchNotFoundError(f"No Level 2 batch with id {batch_id}.")
	harvested_at = harvested_at.replace(tzinfo=None)
	if harvested_at < batch.moved_at:
		raise ValueError("A batch can't be harvested before it moved to Level 2.")
	batch.harvested_at = harvested_at
	session.add(batch)
	await session.commit()
	return batch
