import cv2
import numpy as np
import pytest

from leafy_cv.segment import DEFAULT_WEIGHTS, PAD_LABEL, build_prompts


def test_prompts_put_the_point_first_then_its_negatives_then_padding():
	points = np.array([[10, 10], [50, 10], [90, 10]], np.float32)
	coords, labels = build_prompts(points, [[1], [0, 2], []])
	assert coords.shape == (3, 3, 2) and labels.shape == (3, 3)
	assert labels[0].tolist() == [1, 0, PAD_LABEL]
	assert labels[1].tolist() == [1, 0, 0]
	assert labels[2].tolist() == [1, PAD_LABEL, PAD_LABEL]
	assert coords[1, 0].tolist() == [50, 10] and coords[1, 2].tolist() == [90, 10]


def test_prompts_without_negatives():
	coords, labels = build_prompts(np.array([[1, 2], [3, 4]]))
	assert coords.shape == (2, 1, 2) and (labels == 1).all()


def test_negatives_must_match_points():
	with pytest.raises(ValueError):
		build_prompts(np.array([[1, 2]]), [[], []])


@pytest.mark.skipif(not DEFAULT_WEIGHTS.exists(), reason="MobileSAM weights not downloaded")
def test_mobilesam_outlines_a_green_disk():
	from leafy_cv.segment import Segmenter

	image = np.full((256, 256, 3), 230, np.uint8)
	cv2.circle(image, (128, 128), 50, (60, 160, 70), -1)
	truth = np.zeros((256, 256), np.uint8)
	cv2.circle(truth, (128, 128), 50, 1, -1)
	segmenter = Segmenter(threads=2)
	segmenter.set_image(image)
	[result] = segmenter.predict(np.array([[128, 128]]))
	mask = result.masks[result.best]
	iou = (mask & truth.astype(bool)).sum() / (mask | truth.astype(bool)).sum()
	assert result.masks.shape == (3, 256, 256) and iou > 0.85
