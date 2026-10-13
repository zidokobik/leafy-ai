from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.schemas.chat import ChatRequest


def test_answer_detail_defaults_to_simple():
	# The AI SDK also sends fields such as `trigger`; they are ignored.
	request = ChatRequest.model_validate({"id": str(uuid4()), "messages": [], "trigger": "submit-message"})
	assert request.detail == "simple"


def test_answer_detail_accepts_only_known_styles():
	assert ChatRequest.model_validate({"id": str(uuid4()), "messages": [], "detail": "detailed"}).detail == "detailed"
	with pytest.raises(ValidationError):
		ChatRequest.model_validate({"id": str(uuid4()), "messages": [], "detail": "verbose"})
