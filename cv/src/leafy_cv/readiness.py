"""Turn per-frame numbers into a status per hole (and per zone): the readiness rule.

Written rule (7 Oct, no grower round: Pearl decided not to wait; corrected 12 Oct): **a plant is crowded
when its leaves meet the leaves of a neighbouring plant, in the same channel or in the next channel**,
measured as `boundary_contact` (for the partner it touches most, in either direction: the share of lines
between the two plants along which leaves run continuously, with no visible board between; see metrics.py)
of at least `CONTACT_CROWDED`. Channel expansion separates the plants in the same channel; plants touching
the next channel also need space before they go to Level 2. The 7 Oct rule counted only the next channel,
from a misunderstanding of how expansion works; the thresholds below were not changed by the correction.
Crowding only counts once it has lasted `CONFIRM_FRAMES` usable frames in a row, so one windy or badly
lit hour can't raise an alert.

Statuses (the `plant_observations.status` values agreed in the CV build guide):
- `empty`: coverage under `EMPTY_COVERAGE` (no plant, or one too small to see).
- `growing`: a plant, not crowded.
- `candidate`: crowded, but not yet for CONFIRM_FRAMES frames in a row.
- `ready`: crowded for CONFIRM_FRAMES frames in a row: the grower checks it and expands (a manual job).
- `uncertain`: can't judge: the hole is mostly outside the frame, or has no partner line inside the frame.

Smoothing: contact is the median of the last `SMOOTH_FRAMES` usable frames (only past frames, so it works
live), which ignores one-frame outline glitches. 7 Oct: it halved status changes (camera 2 current layout
2.49 -> 1.12 per hole per day; 22-30 Sep 0.68 -> 0.44) without delaying when holes first became ready.
When the window holds only 2 values (the first 2 frames of a period, or right after a frame without a
value) the lower one is used, not their average, so a streak needs 2 frames that agree (rule-v4, 8 Oct,
from the independent review: with the average, [0.80, 1.0, 0.85, 0.85] made a zone ready on one frame
over 0.9). Changed 5 holes on the archived frames (1-2 frames later), no zone. The window counts usable
frames, not hours: the overnight break and any camera outage are bridged.

Hysteresis: once crowded, a hole stays crowded until contact drops below CONTACT_CROWDED - HYSTERESIS,
so values hovering at the threshold don't flip the status every hour.

Zones (closed canopy measured as a whole) use the same smoothing and streak with `closure >= ZONE_CLOSED`
as "crowded", and are never `empty`. Zone smoothing (rule-v3, 8 Oct): without it, the 0.85-0.9 hysteresis
band let a single frame over 0.9 start a streak that frames under 0.9 then finished (camera 1 dense_far:
one frame at 0.901, then 0.851 and 0.894, was "ready" from 2 Oct 06:00 while the canopy sat at 0.87-0.91).
With it, camera 1 is ready 10 frames later (2 Oct 16:00), camera 2 one frame later (23 Sep 05:00, still
well before the 30 Sep sanity check), camera 3 unchanged; status changes per zone unchanged (2, 2, 1).
Side effect: 2 closed frames in every 3 now count as closed (0.92, 0.80, 0.92, 0.92 reaches ready).

The thresholds are the written rule's starting values. They are checked against our own labels of
hole crops (the grower round replacement) and the 30 Sep sanity check, and changed only there, with
the change and its reason recorded.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise
from statistics import median_low

EMPTY_COVERAGE = 0.05
CONTACT_CROWDED = 0.5
ZONE_CLOSED = 0.9
HYSTERESIS = 0.05
CONFIRM_FRAMES = 3
SMOOTH_FRAMES = 3
RULE_VERSION = "rule-v5"  # v3 (8 Oct): zones smoothed like holes; v4: lower value when the window has 2;
# v5 (12 Oct): contact in both directions (same channel and next channel); thresholds unchanged


class HoleStatus(StrEnum):
	"""The plant_observations.status values (written to the CSVs as these strings)."""

	EMPTY = "empty"
	GROWING = "growing"
	CANDIDATE = "candidate"
	READY = "ready"
	UNCERTAIN = "uncertain"


EMPTY, GROWING, CANDIDATE, READY, UNCERTAIN = (
	HoleStatus.EMPTY,
	HoleStatus.GROWING,
	HoleStatus.CANDIDATE,
	HoleStatus.READY,
	HoleStatus.UNCERTAIN,
)


@dataclass(frozen=True)
class Status:
	status: HoleStatus
	confirmed_frames: int  # length of the current crowded streak (0 when not crowded)


def rolling_median(values: Sequence[float | None], frames: int) -> list[float | None]:
	"""Median of each value and the frames - 1 before it (None values skipped; None stays None).

	With an even number of values (2 at the start or after a gap) the lower middle value is used.
	"""
	out = []
	for k, value in enumerate(values):
		window = [v for v in values[max(0, k - frames + 1) : k + 1] if v is not None]
		out.append(None if value is None else float(median_low(window)))
	return out


def crowding_statuses(
	values: Sequence[float | None], threshold: float, empty: Sequence[bool] | None = None
) -> list[Status]:
	"""The streak rule shared by holes and zones, frame by frame (oldest first): no value -> uncertain; `empty` ->
	empty; otherwise crowded at `threshold` or more (once crowded, until HYSTERESIS below it), and ready after
	CONFIRM_FRAMES crowded frames in a row."""
	out, streak, crowded = [], 0, False
	for k, value in enumerate(values):
		if value is None or (empty is not None and empty[k]):
			out.append(Status(UNCERTAIN if value is None else EMPTY, 0))
			streak, crowded = 0, False
			continue
		crowded = value >= (threshold - HYSTERESIS if crowded else threshold)
		streak = streak + 1 if crowded else 0
		out.append(Status((READY if streak >= CONFIRM_FRAMES else CANDIDATE) if crowded else GROWING, streak))
	return out


def hole_statuses(
	coverage: Sequence[float],
	contact: Sequence[float | None],
	*,
	reliable: bool = True,
	smooth_frames: int = SMOOTH_FRAMES,
) -> list[Status]:
	"""Statuses of one hole over its usable frames, oldest first."""
	if len(coverage) != len(contact):
		raise ValueError("coverage and contact need one value per frame")
	if not reliable:
		return [Status(UNCERTAIN, 0) for _ in coverage]
	empty = [cov < EMPTY_COVERAGE for cov in coverage]
	return crowding_statuses(rolling_median(contact, smooth_frames), CONTACT_CROWDED, empty)


def zone_statuses(
	closure: Sequence[float],
	*,
	smooth_frames: int = SMOOTH_FRAMES,
) -> list[Status]:
	"""Statuses of one zone over its usable frames, oldest first: a closed canopy is crowded.

	Closure is smoothed like hole contact. NaN (zone not measurable) becomes None first, because
	rolling_median skips None but would put a NaN inside the median; it stays None (uncertain) after."""
	present = [None if math.isnan(v) else v for v in closure]
	return crowding_statuses(rolling_median(present, smooth_frames), ZONE_CLOSED)


def flip_rate(statuses: Sequence[str], days: float) -> float:
	"""Status changes per day for one hole (lower = steadier)."""
	if days <= 0:
		return 0.0
	changes = sum(1 for a, b in pairwise(statuses) if a != b)
	return changes / days
