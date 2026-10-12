"""tools/make_hole_items.py (stratified crops) and tools/evaluate_readiness.py (per camera, per status).

Agreed 11 Oct, before any labels: every camera gets each status, camera 2's first days after the 30 Sep
transfer are covered, one crop per hole per day, and the catch rate is weighted back to the population.
"""

import importlib.util
import random
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def load(name):
	spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


@pytest.fixture
def items():
	return load("make_hole_items")


@pytest.fixture
def evaluate():
	return load("evaluate_readiness")


def row(camera, hole, when, status, contact=0.5, period="P3", row_no="3"):
	return {
		"camera_id": camera,
		"hole_id": hole,
		"captured_at": when,
		"status": status,
		"boundary_contact": str(contact),
		"period": period,
		"image_id": f"{camera}_{when}.jpg",
		"row": row_no,
	}


def make_pool():
	pool = []
	for day in range(1, 9):
		for hour in (9, 12, 15):
			for h in range(12):
				when = f"2026-10-0{day}T{hour:02d}:00:00"
				status = ("ready", "growing", "candidate", "growing")[h % 4]
				pool.append(row("level1_camera1", f"H{h:02d}", when, status, contact=(h % 5) / 5))
	for day in ("2026-09-30", "2026-10-01"):  # the two days after the transfer: 20 ready + 20 growing hole-days
		for hour in (11, 13, 15, 17):
			for h in range(20):
				pool.append(row("level1_camera2", f"E{h:02d}", f"{day}T{hour}:00:00", ("ready", "growing")[h % 2]))
	for day in range(2, 9):  # later camera 2 days, which the regular quotas would otherwise fill from
		for h in range(40):
			pool.append(row("level1_camera2", f"E{h:02d}", f"2026-10-0{day}T12:00:00", ("ready", "growing")[h % 2]))
	pool.append(row("level1_camera2", "OLD", "2026-09-30T09:00:00", "ready", period="P2"))  # before the transfer
	return pool


def test_quotas_one_crop_per_hole_day_and_scarce_statuses_first(items):
	picked, strata = items.pick_items(make_pool(), random.Random(0))
	keys = [items.hole_day(r) for r in picked]
	assert len(keys) == len(set(keys))
	for (camera, status), (available, n) in strata.items():
		assert n <= min(items.QUOTAS[status], available)
	# camera 1: 3 candidate holes x 8 days = 24 hole-days, so the quota of 12 is met despite sharing days
	assert strata[("level1_camera1", "candidate")][1] == items.QUOTAS["candidate"]


def test_camera_2_first_days_after_the_transfer_are_covered(items):
	picked, _ = items.pick_items(make_pool(), random.Random(0))
	early = [r for r in picked if r["camera_id"] == "level1_camera2" and r["captured_at"] >= items.EARLY_FROM]
	ready = sum(r["status"] == "ready" for r in early)
	growing = sum(r["status"] == "growing" for r in early)
	assert ready >= items.EARLY_QUOTAS["ready"] and growing >= items.EARLY_QUOTAS["growing"]
	assert all(r["hole_id"] != "OLD" for r in early)  # 30 Sep before 11:00 is the old layout


def test_growing_crops_spread_over_contact(items):
	picked, _ = items.pick_items(make_pool(), random.Random(0))
	growing = [r for r in picked if r["camera_id"] == "level1_camera1" and r["status"] == "growing"]
	assert len({items.spread_key(r) for r in growing}) >= 3


def test_wilson_interval(evaluate):
	lo, hi = evaluate.wilson(8, 10)
	assert 0.44 < lo < 0.5 and 0.94 < hi < 0.97
	assert evaluate.wilson(0, 0)[0] != evaluate.wilson(0, 0)[0]  # NaN for no crops


def test_catch_rate_is_weighted_back_to_the_population(evaluate):
	# 10 crowded crops among ready (each stands for 10 plants), 10 among growing (each stands for 1)
	crowded = {"ready": 10, "growing": 10}
	weights = {"ready": 10.0, "growing": 1.0}
	assert evaluate.weighted_catch(crowded, weights, ("ready",)) == pytest.approx(100 / 110)
	assert evaluate.weighted_catch(crowded, {"ready": 1.0, "growing": 1.0}, ("ready",)) == pytest.approx(0.5)


def test_catch_interval_is_not_zero_width_when_every_crop_agrees(evaluate):
	rows = [{"status": "ready", "label": "crowded"}] * 10 + [{"status": "growing", "label": "not_crowded"}] * 10
	rows += [{"status": "growing", "label": "crowded"}]
	lo, hi = evaluate.catch_interval(rows, {"ready": 2.0, "growing": 5.0}, ("ready",))
	assert lo < hi
	point = evaluate.weighted_catch({"ready": 10, "growing": 1}, {"ready": 2.0, "growing": 5.0}, ("ready",))
	assert lo <= point <= hi


def test_report_counts_caught_candidate_and_missed(evaluate):
	rows = (
		[{"status": "ready", "label": "crowded"}] * 4
		+ [{"status": "candidate", "label": "crowded"}] * 2
		+ [{"status": "growing", "label": "crowded"}] * 3
		+ [{"status": "growing", "label": "not_crowded"}] * 5
	)
	report = evaluate.camera_report(rows, {s: 1.0 for s in evaluate.STATUSES})
	assert (report.caught, report.candidate, report.missed) == (4, 2, 3)
	assert report.status["growing"][:2] == (3, 8)
	assert report.catch == pytest.approx(4 / 9)
