import logging
import time

import ai

logger = logging.getLogger(__name__)


@ai.tool
async def get_unix_timestamp():
	"""
	Returns the current Unix timestamp in seconds.
	"""
	logger.info("`get_unix_timestamp` called")
	return time.time()
