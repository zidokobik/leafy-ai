# Frame, move and harvest times are farm local time without a timezone, as stored in the database.
# ruff: noqa: DTZ001
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from backend.db_models.level2_batches import Level2Batch
from backend.schemas.harvest_readiness import HarvestStatus
from backend.services import harvest_readiness
from backend.services.harvest_readiness import (
	MESSAGES,
	NOTHING_ON_LEVEL2,
	BatchNotFoundError,
	get_harvest_readiness,
	harvest_status,
	record_harvest,
	summarise,
	to_batch_harvest,
)

# The two moves in the archived frames: 30 Sep (harvested 7 Oct) and 8 Oct (not harvested yet).
FIRST = Level2Batch(id=1, moved_at=datetime(2026, 9, 30, 11, 0, 27), harvested_at=datetime(2026, 10, 7, 17, 0, 36))
SECOND = Level2Batch(id=2, moved_at=datetime(2026, 10, 8, 16, 0, 30), note="moved 8 Oct")


@pytest.mark.parametrize(
	("days", "expected"),
	[
		(0, HarvestStatus.GROWING),
		(5.99, HarvestStatus.GROWING),
		(6, HarvestStatus.HARVEST_TOMORROW),  # one day before it is due
		(6.99, HarvestStatus.HARVEST_TOMORROW),
		(7, HarvestStatus.HARVEST_DUE),
		(10, HarvestStatus.HARVEST_DUE),  # stays due until a harvest is recorded
	],
)
def test_harvest_status_window(days, expected):
	assert harvest_status(SECOND, SECOND.moved_at + timedelta(days=days)) is expected


def test_harvest_status_uses_the_recorded_harvest():
	assert harvest_status(FIRST, datetime(2026, 10, 7, 12)) is HarvestStatus.HARVEST_DUE, "before the harvest hour"
	assert harvest_status(FIRST, datetime(2026, 10, 7, 18)) is HarvestStatus.HARVESTED


def test_to_batch_harvest():
	due = to_batch_harvest(SECOND, datetime(2026, 10, 15, 16, 1))
	assert due.status is HarvestStatus.HARVEST_DUE and due.message == MESSAGES[HarvestStatus.HARVEST_DUE]
	assert due.due_at == datetime(2026, 10, 15, 16, 0, 30)
	assert due.days_on_level2 == 7.0 and due.harvested_at is None and due.note == "moved 8 Oct"

	# A harvested batch counts its days up to the harvest, not up to as_of.
	harvested = to_batch_harvest(FIRST, datetime(2026, 10, 13, 12))
	assert harvested.status is HarvestStatus.HARVESTED
	assert harvested.days_on_level2 == 7.3 and harvested.harvested_at == FIRST.harvested_at

	# A harvest recorded after as_of is not shown yet (replaying an earlier day).
	assert to_batch_harvest(FIRST, datetime(2026, 10, 5, 12)).harvested_at is None


def test_summarise():
	assert summarise([]) == NOTHING_ON_LEVEL2
	assert summarise([to_batch_harvest(FIRST, datetime(2026, 10, 13))]) == NOTHING_ON_LEVEL2
	growing = to_batch_harvest(SECOND, datetime(2026, 10, 13, 21, 46))
	assert summarise([growing]) == "Next harvest due 15 Oct 16:00"
	tomorrow = to_batch_harvest(SECOND, datetime(2026, 10, 14, 17))
	assert summarise([tomorrow]) == "1 batch due tomorrow"
	due = to_batch_harvest(SECOND, datetime(2026, 10, 16))
	also_due = to_batch_harvest(FIRST, datetime(2026, 10, 7, 12))
	assert summarise([due, also_due, tomorrow]) == "2 batches due for harvest, 1 batch due tomorrow"


def batches_session(batches: list[Level2Batch]):
	result = MagicMock()
	result.scalars.return_value = batches
	session = MagicMock()
	session.execute = AsyncMock(return_value=result)
	session.get = AsyncMock(return_value=None)
	session.add = MagicMock()
	session.commit = AsyncMock()
	return session


@pytest.mark.asyncio
async def test_get_harvest_readiness_as_of():
	session = batches_session([SECOND, FIRST])
	result = await get_harvest_readiness(session, datetime(2026, 10, 14, 17, tzinfo=UTC))

	assert result.as_of == datetime(2026, 10, 14, 17), "a timezone is dropped: batch times are farm local time"
	assert [batch.status for batch in result.batches] == [HarvestStatus.HARVEST_TOMORROW, HarvestStatus.HARVESTED]
	assert result.summary == "1 batch due tomorrow"
	query = session.execute.await_args.args[0].compile(dialect=postgresql.dialect())
	assert "moved_at <=" in str(query) and "ORDER BY level2_batches.moved_at DESC" in str(query)


@pytest.mark.asyncio
async def test_get_harvest_readiness_defaults_to_farm_now(monkeypatch):
	monkeypatch.setattr(harvest_readiness, "farm_now", lambda: datetime(2026, 10, 15, 16, 30))
	result = await get_harvest_readiness(batches_session([SECOND]))
	assert result.as_of == datetime(2026, 10, 15, 16, 30)
	assert result.summary == "1 batch due for harvest"


@pytest.mark.asyncio
async def test_record_harvest():
	session = batches_session([])
	with pytest.raises(BatchNotFoundError):
		await record_harvest(session, 99, datetime(2026, 10, 15, 17))

	batch = Level2Batch(id=2, moved_at=SECOND.moved_at)
	session.get.return_value = batch
	with pytest.raises(ValueError):
		await record_harvest(session, 2, datetime(2026, 10, 8, 12))
	session.commit.assert_not_awaited()

	harvested = await record_harvest(session, 2, datetime(2026, 10, 15, 17, tzinfo=UTC))
	assert harvested.harvested_at == datetime(2026, 10, 15, 17)
	session.commit.assert_awaited_once()
