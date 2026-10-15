"""Switch outlets on Kasa powerboards (power strips) with python-kasa.

Every call discovers the board by host, runs one command and disconnects; nothing is
kept between calls. Calls to the same host are serialized so two commands never talk
to one board at the same time.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from kasa import AuthenticationError, Credentials, Device, DeviceError, Discover, KasaException, UnsupportedDeviceError

from backend.settings import get_settings

logger = logging.getLogger(__name__)

# Discovery alone waits up to 5 s for a board that does not answer; this bounds the whole call.
TIMEOUT_SECONDS = 20

_host_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class PowerboardError(Exception):
	"""The powerboard could not be reached or did not carry out the command."""


async def read_outlets(host: str) -> list[bool]:
	"""On/off state of every outlet on the board, in outlet order (index 0 is outlet 1)."""

	async def read(board: Device) -> list[bool]:
		return [outlet.is_on for outlet in board.children]

	return await _with_board(host, read)


async def set_outlet(host: str, outlet_num: int, *, on: bool) -> None:
	"""Switch one outlet (1-based) on or off, then confirm the board reports the new state."""

	async def switch(board: Device) -> None:
		outlet = _outlet(board, host, outlet_num)
		if on:
			await outlet.turn_on()
		else:
			await outlet.turn_off()
		await board.update()
		if outlet.is_on != on:
			raise PowerboardError(f"Outlet {outlet_num} on {host} still reports {'off' if on else 'on'}.")

	await _with_board(host, switch)


def _outlet(board: Device, host: str, outlet_num: int) -> Device:
	outlets = board.children
	if not outlets:
		raise PowerboardError(f"{host} reports no outlets; is it a Kasa power strip?")
	if not 1 <= outlet_num <= len(outlets):
		raise PowerboardError(f"{host} has {len(outlets)} outlets; outlet {outlet_num} does not exist.")
	return outlets[outlet_num - 1]


def _credentials() -> Credentials | None:
	settings = get_settings()
	if settings.KASA_USERNAME and settings.KASA_PASSWORD:
		return Credentials(settings.KASA_USERNAME, settings.KASA_PASSWORD.get_secret_value())
	return None


async def _with_board[T](host: str, operation: Callable[[Device], Awaitable[T]]) -> T:
	async with _host_locks[host]:
		board: Device | None = None
		try:
			async with asyncio.timeout(TIMEOUT_SECONDS):
				board = await Discover.discover_single(host, credentials=_credentials())
				if board is None:
					raise PowerboardError(f"{host} is not a supported Kasa device.")
				await board.update()
				return await operation(board)
		except (KasaException, OSError) as error:
			raise PowerboardError(_describe(host, error)) from error
		finally:
			if board is not None:
				await _disconnect(board)


def _describe(host: str, error: Exception) -> str:
	detail = str(error) or type(error).__name__
	# kasa's TimeoutError subclasses the builtin one, which also covers asyncio.timeout.
	if isinstance(error, TimeoutError):
		return f"Powerboard {host} did not respond. Check it is powered on and on the same network as the server."
	if isinstance(error, AuthenticationError):
		return f"Powerboard {host} needs valid TP-Link account credentials (KASA_USERNAME and KASA_PASSWORD in .env)."
	if isinstance(error, UnsupportedDeviceError):
		return f"{host} is not a supported Kasa device: {detail}"
	if isinstance(error, DeviceError):
		return f"Powerboard {host} rejected the command: {detail}"
	return f"Could not reach powerboard {host}: {detail}"


async def _disconnect(board: Device) -> None:
	try:
		await board.disconnect()
	except Exception:
		logger.debug("Closing the connection to %s failed", board.host, exc_info=True)
