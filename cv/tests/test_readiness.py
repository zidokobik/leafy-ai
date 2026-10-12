import pytest

from leafy_cv.readiness import (
	CANDIDATE,
	EMPTY,
	GROWING,
	READY,
	UNCERTAIN,
	flip_rate,
	hole_statuses,
	rolling_median,
	zone_statuses,
)


def names(statuses):
	return [s.status for s in statuses]


def test_ready_only_after_three_crowded_frames_in_a_row():
	result = hole_statuses([0.5] * 5, [0.2, 0.6, 0.6, 0.6, 0.6], smooth_frames=1)
	assert names(result) == [GROWING, CANDIDATE, CANDIDATE, READY, READY]
	assert [s.confirmed_frames for s in result] == [0, 1, 2, 3, 4]


def test_one_open_frame_breaks_the_streak():
	result = hole_statuses([0.5] * 5, [0.6, 0.6, 0.3, 0.6, 0.6], smooth_frames=1)
	assert names(result) == [CANDIDATE, CANDIDATE, GROWING, CANDIDATE, CANDIDATE]


def test_hysteresis_keeps_a_hole_crowded_just_under_the_threshold():
	# 0.47 is under 0.5 but above 0.5 - 0.05: still crowded once crowded
	assert names(hole_statuses([0.5] * 4, [0.6, 0.47, 0.47, 0.6], smooth_frames=1)) == [
		CANDIDATE,
		CANDIDATE,
		READY,
		READY,
	]
	# but 0.47 alone never starts a streak
	assert names(hole_statuses([0.5] * 2, [0.47, 0.47], smooth_frames=1)) == [GROWING, GROWING]
	# and 0.44 ends it
	assert names(hole_statuses([0.5] * 2, [0.6, 0.44], smooth_frames=1)) == [CANDIDATE, GROWING]


def test_empty_hole_is_never_crowded_even_if_a_neighbours_leaves_reach_it():
	assert names(hole_statuses([0.02, 0.02], [0.9, 0.9])) == [EMPTY, EMPTY]


def test_holes_we_cannot_judge_are_uncertain():
	assert names(hole_statuses([0.5, 0.5], [0.9, 0.9], reliable=False)) == [UNCERTAIN, UNCERTAIN]
	assert names(hole_statuses([0.5], [None])) == [UNCERTAIN]


def test_mismatched_lengths_are_refused():
	with pytest.raises(ValueError):
		hole_statuses([0.5], [0.5, 0.5])


def test_zone_closes_after_three_frames_and_nan_is_uncertain():
	assert names(zone_statuses([0.95, 0.95, 0.95, float("nan"), 0.7])) == [
		CANDIDATE,
		CANDIDATE,
		READY,
		UNCERTAIN,
		GROWING,
	]


def test_zone_closure_is_smoothed_and_nan_stays_uncertain():
	nan = float("nan")
	# one low hour no longer resets a closed zone
	assert names(zone_statuses([0.95, 0.95, 0.95, 0.95, 0.70, 0.95])) == [
		CANDIDATE,
		CANDIDATE,
		READY,
		READY,
		READY,
		READY,
	]
	assert names(zone_statuses([0.95, 0.95, 0.95, 0.95, 0.70, 0.95], smooth_frames=1))[4] == GROWING
	# a frame that can't be measured stays uncertain, and is left out of its neighbours' medians
	result = names(zone_statuses([0.95, 0.95, nan, 0.95, 0.70]))
	assert result[2] == UNCERTAIN and result[3] == CANDIDATE  # median of 0.95 and 0.95, not NaN
	assert rolling_median([0.95, None, 0.70], 3)[-1] == 0.70 and result[4] == GROWING
	# side effect: 2 closed frames of every 3 now count as closed (never ready without smoothing)
	noisy = [0.92, 0.80, 0.92, 0.92, 0.80]
	assert READY not in names(zone_statuses(noisy, smooth_frames=1))
	assert names(zone_statuses(noisy))[-1] == READY


def test_one_high_frame_cannot_start_a_streak_at_the_start_or_after_a_gap():
	# independent review, 8 Oct: with the average of 2, these reached ready on one high frame
	assert READY not in names(zone_statuses([0.80, 1.0, 0.85, 0.85]))
	assert READY not in names(hole_statuses([0.5] * 4, [0.3, 0.7, 0.47, 0.47]))
	# the same after a frame without a value (hole) or an unmeasurable frame (zone)
	assert READY not in names(hole_statuses([0.5] * 7, [0.6, None, None, 0.3, 0.7, 0.47, 0.47]))
	nan = float("nan")
	assert READY not in names(zone_statuses([0.95, nan, nan, 0.80, 1.0, 0.85, 0.85]))
	# two frames that agree still start a streak straight away
	assert names(zone_statuses([0.95, 0.95, 0.95])) == [CANDIDATE, CANDIDATE, READY]
	assert names(hole_statuses([0.5] * 3, [0.6, 0.6, 0.6])) == [CANDIDATE, CANDIDATE, READY]


def test_flip_rate_counts_changes_per_day():
	assert flip_rate([GROWING, GROWING, CANDIDATE, GROWING], days=2) == 1.0
	assert flip_rate([GROWING], days=0) == 0.0


def test_one_odd_frame_is_smoothed_away():
	# 7 Oct, camera 2 far rows: one-frame outline glitches made contact jump 0.03 -> 0.63 -> 0.05
	assert names(hole_statuses([0.5] * 5, [0.1, 0.1, 0.9, 0.1, 0.1])) == [GROWING] * 5
	# a lasting change still gets through, one frame later than without smoothing
	contact = [0.1, 0.1, 0.9, 0.9, 0.9, 0.9]
	smoothed = [GROWING, GROWING, GROWING, CANDIDATE, CANDIDATE, READY]
	assert names(hole_statuses([0.5] * 6, contact)) == smoothed
	assert names(hole_statuses([0.5] * 6, contact, smooth_frames=1)) == [GROWING, *smoothed[2:], READY]
	# the window is the last 3 frames; a frame without a value just has nothing to add
	assert rolling_median([0.1, None, 0.9, 0.5], 3) == [0.1, None, 0.1, 0.5]
