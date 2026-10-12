import cv2
import numpy as np
import pytest

from leafy_cv.plant_filter import FEATURE_NAMES, PlantFilter, mask_features, pack_masks, unpack_masks


def textured(colour_bgr, size=(200, 200), seed=0) -> np.ndarray:
	rng = np.random.default_rng(seed)
	noise = rng.normal(0, 12, (*size, 1))
	return np.clip(np.array(colour_bgr, np.float32) + noise, 0, 255).astype(np.uint8)


def disk(radius, size=(200, 200)) -> np.ndarray:
	mask = np.zeros(size, np.uint8)
	cv2.circle(mask, (100, 100), radius, 1, -1)
	return mask.astype(bool)


def test_features_do_not_depend_on_mask_size():
	image = textured((60, 160, 70))  # leaf green
	small, big = mask_features(image, disk(15)), mask_features(image, disk(90))
	assert len(small) == len(FEATURE_NAMES)
	np.testing.assert_allclose(small, big, atol=0.03)


def test_green_scores_higher_excess_green_than_board():
	exg = FEATURE_NAMES.index("exg_mean")
	leaf = mask_features(textured((60, 160, 70)), disk(50))
	board = mask_features(textured((225, 215, 230)), disk(50))  # white board, magenta tint
	assert leaf[exg] > board[exg] + 0.1


def test_tiny_masks_are_rejected():
	with pytest.raises(ValueError):
		mask_features(textured((60, 160, 70)), disk(1))


def test_filter_round_trip_and_probability(tmp_path):
	n = len(FEATURE_NAMES)
	plant_filter = PlantFilter(
		feature_names=FEATURE_NAMES, mean=np.zeros(n), scale=np.ones(n), weights=np.ones(n), bias=-1.0
	)
	path = tmp_path / "filter.json"
	plant_filter.save(path)
	loaded = PlantFilter.load(path)
	x = np.full(n, 0.1)
	assert loaded.probability(x)[0] == pytest.approx(1 / (1 + np.exp(-(0.1 * n - 1.0))))
	assert loaded.is_plant(np.ones(n))[0] and not loaded.is_plant(np.zeros(n))[0]


def test_filter_trained_on_other_features_is_refused(tmp_path):
	path = tmp_path / "filter.json"
	path.write_text(
		'{"feature_names": ["old"], "mean": [0], "scale": [1], "weights": [1], "bias": 0, "threshold": 0.5}'
	)
	with pytest.raises(ValueError):
		PlantFilter.load(path)


def test_mask_packing_round_trip():
	rng = np.random.default_rng(0)
	masks = rng.random((3, 17, 701)) > 0.5  # width not a multiple of 8
	assert (unpack_masks(pack_masks(masks), 701) == masks).all()
