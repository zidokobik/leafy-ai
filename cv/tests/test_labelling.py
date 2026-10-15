"""The labelling session shared by label_holes.py and label_masks.py (no window needed)."""

import numpy as np

from leafy_cv.drawing import dim_outside
from leafy_cv.labelling import LabelSession

ITEMS = [{"item_id": f"i{k}"} for k in range(4)]


def test_answers_move_on_and_back_takes_the_last_answer_back():
	session = LabelSession(ITEMS, "item_id", [])
	session.answer("crowded", "t")
	session.answer("empty", "t")
	assert session.current["item_id"] == "i2" and [r["label"] for r in session.labels] == ["crowded", "empty"]
	session.back()
	assert session.current["item_id"] == "i1" and len(session.labels) == 1
	assert session.count("crowded") == 1 and session.count("empty") == 0


def test_resumes_after_the_answered_items_and_back_reaches_into_the_earlier_session():
	session = LabelSession(ITEMS, "item_id", [{"item_id": "i0", "label": "crowded", "labelled_at": "t"}])
	assert [i["item_id"] for i in session.queue] == ["i1", "i2", "i3"]
	session.back()  # i0 was answered in an earlier session: it is put back in front
	assert session.current["item_id"] == "i0" and session.labels == []
	session.back()  # nothing left to take back
	assert session.current["item_id"] == "i0"


def test_back_over_an_answer_for_an_item_that_no_longer_exists_does_not_crash():
	session = LabelSession(ITEMS, "item_id", [{"item_id": "gone", "label": "crowded", "labelled_at": "t"}])
	session.back()
	assert session.labels == [] and session.current["item_id"] == "i0"


def test_session_ends_when_every_item_is_answered():
	session = LabelSession(ITEMS[:1], "item_id", [])
	session.answer("unsure", "t")
	assert session.current is None


def test_dim_outside_keeps_the_mask_and_darkens_the_rest():
	image = np.full((2, 2, 3), 200, np.uint8)
	mask = np.array([[True, False], [False, False]])
	out = dim_outside(image, mask)
	assert out[0, 0].tolist() == [200, 200, 200] and out[1, 1].tolist() == [70, 70, 70]
	assert image[1, 1].tolist() == [200, 200, 200]  # the original is untouched
