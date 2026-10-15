import pytest
from kasa import AuthenticationError
from kasa import TimeoutError as KasaTimeoutError

from backend.services import outlets

HOST = "10.0.0.5"


class FakeOutlet:
	def __init__(self, on: bool = False):
		self.is_on = on
		self.stuck = False

	async def turn_on(self):
		self.is_on = self.is_on or not self.stuck
		return {}

	async def turn_off(self):
		self.is_on = self.is_on and self.stuck
		return {}


class FakeBoard:
	host = HOST

	def __init__(self, children: list[FakeOutlet], update_error: Exception | None = None):
		self.children = children
		self.update_error = update_error
		self.disconnected = False

	async def update(self):
		if self.update_error:
			raise self.update_error

	async def disconnect(self):
		self.disconnected = True


@pytest.fixture
def discover(monkeypatch):
	"""Make Discover.discover_single return (or raise) whatever the test sets."""
	found: dict = {}

	async def discover_single(host, **kwargs):
		found["host"] = host
		if isinstance(found.get("result"), Exception):
			raise found["result"]
		return found["result"]

	monkeypatch.setattr(outlets.Discover, "discover_single", discover_single)
	monkeypatch.setattr(outlets, "_credentials", lambda: None)
	return found


@pytest.mark.asyncio
async def test_set_outlet_uses_one_based_outlets_and_disconnects(discover):
	board = FakeBoard([FakeOutlet(), FakeOutlet(), FakeOutlet()])
	discover["result"] = board

	await outlets.set_outlet(HOST, 2, on=True)
	assert [outlet.is_on for outlet in board.children] == [False, True, False]
	await outlets.set_outlet(HOST, 2, on=False)
	assert not board.children[1].is_on
	assert discover["host"] == HOST
	assert board.disconnected


@pytest.mark.asyncio
async def test_read_outlets_in_outlet_order(discover):
	discover["result"] = FakeBoard([FakeOutlet(), FakeOutlet(on=True)])
	assert await outlets.read_outlets(HOST) == [False, True]


@pytest.mark.asyncio
async def test_missing_outlet_is_reported(discover):
	board = FakeBoard([FakeOutlet(), FakeOutlet()])
	discover["result"] = board
	with pytest.raises(outlets.PowerboardError, match="has 2 outlets; outlet 3 does not exist"):
		await outlets.set_outlet(HOST, 3, on=True)
	assert board.disconnected

	discover["result"] = FakeBoard([])
	with pytest.raises(outlets.PowerboardError, match="no outlets"):
		await outlets.set_outlet(HOST, 1, on=True)


@pytest.mark.asyncio
async def test_unconfirmed_switch_is_an_error(discover):
	board = FakeBoard([FakeOutlet(on=True)])
	board.children[0].stuck = True
	discover["result"] = board
	with pytest.raises(outlets.PowerboardError, match="still reports on"):
		await outlets.set_outlet(HOST, 1, on=False)


@pytest.mark.asyncio
async def test_unreachable_board_is_a_powerboard_error(discover):
	discover["result"] = KasaTimeoutError(f"Timed out getting discovery response for {HOST}")
	with pytest.raises(outlets.PowerboardError, match="did not respond"):
		await outlets.read_outlets(HOST)


@pytest.mark.asyncio
async def test_authentication_failure_names_the_settings(discover):
	board = FakeBoard([FakeOutlet()], update_error=AuthenticationError("Tapo plug requires authentication."))
	discover["result"] = board
	with pytest.raises(outlets.PowerboardError, match="KASA_USERNAME"):
		await outlets.set_outlet(HOST, 1, on=True)
	assert board.disconnected
