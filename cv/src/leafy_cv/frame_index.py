"""Label every frame of one camera and split its history into periods.

A period is a stretch of time where the camera and the layout stay the same, so one hole
map fits every frame in it. A new period starts when the camera moves or the layout changes.

Each frame is compared with the last frame we trust (the "anchor"):
- stable -> OK, and it becomes the new anchor (so slow plant growth is followed). Except the
  first frame of each day: camera 1 is often shifted ~5-8 px then, and morning light differs,
  so it can be OK but never becomes the anchor (it once dragged the anchor and faked a move).
- not stable -> held as "pending" until the next frame decides what it was:
    - next frame is stable vs the anchor  -> the pending frame was a one-off (TRANSIENT_SHIFT)
    - next frame is stable vs the pending -> a lasting change began at the pending frame; new
      period. CAMERA_MOVED if the fixed parts clearly agree on a shift, otherwise
      SCENE_CHANGED: the plants were moved, removed or arrived (or the camera was turned so
      far that its fixed parts are out of view). A person checks the event image and writes
      what it was in periods.csv.
    - neither                             -> the pending frame is marked UNSTABLE
- the last frame, if still pending, is UNCONFIRMED: we need a later frame to decide.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from leafy_cv.drift import Alignment

OK = "ok"
TRANSIENT_SHIFT = "transient_shift"
CAMERA_MOVED = "camera_moved"
SCENE_CHANGED = "scene_changed"
UNSTABLE = "unstable"
UNCONFIRMED = "unconfirmed"

# Frames that are safe to analyse. The first frame of a new period is fine: it just needs
# that period's hole map.
USABLE_STATUSES = {OK, CAMERA_MOVED, SCENE_CHANGED}


@dataclass
class FrameLabel:
	index: int
	status: str
	period: int
	compared_with: int | None
	inliers: int | None
	shift_px: float | None
	rotation_deg: float | None
	plant_change: float | None = None


def _label(index: int, status: str, period: int, compared_with: int | None, alignment: Alignment | None) -> FrameLabel:
	return FrameLabel(
		index=index,
		status=status,
		period=period,
		compared_with=compared_with,
		inliers=alignment.inliers if alignment else None,
		shift_px=alignment.shift_px if alignment else None,
		rotation_deg=alignment.rotation_deg if alignment else None,
		plant_change=alignment.plant_change if alignment else None,
	)


def label_sequence(
	frame_count: int, compare: Callable[[int, int], Alignment], can_anchor: Sequence[bool] | None = None
) -> list[FrameLabel]:
	"""Label frames 0..frame_count-1 of one camera, oldest first.

	`compare(i, j)` returns how frame j is aligned relative to frame i. Passing it in (rather
	than images) keeps this logic testable without any image files. `can_anchor[i]` False means
	frame i may be OK but is never used as the reference (first frames of the day).
	"""
	can_anchor = list(can_anchor) if can_anchor is not None else [True] * frame_count
	if frame_count == 0:
		return []
	labels = [_label(0, OK, 1, None, None)]
	anchor, pending, period = 0, None, 1
	pending_vs_anchor: Alignment | None = None

	for i in range(1, frame_count):
		vs_anchor = compare(anchor, i)
		if vs_anchor.stable:
			if pending is not None:
				labels[pending].status = TRANSIENT_SHIFT
				pending = None
			labels.append(_label(i, OK, period, anchor, vs_anchor))
			if can_anchor[i]:
				anchor = i
			continue

		if pending is not None:
			vs_pending = compare(pending, i)
			if vs_pending.stable:
				period += 1
				start = labels[pending]
				start.status = CAMERA_MOVED if pending_vs_anchor.clear_move else SCENE_CHANGED
				start.period = period
				labels.append(_label(i, OK, period, pending, vs_pending))
				anchor, pending = i, None
				continue
			labels[pending].status = UNSTABLE

		labels.append(_label(i, UNCONFIRMED, period, anchor, vs_anchor))
		pending, pending_vs_anchor = i, vs_anchor

	return labels
