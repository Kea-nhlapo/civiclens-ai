import sys

import numpy as np

from app.detection.detector import Detection, drop_contained, resize_bilinear
from app.detection.issues import crack_issue, find_issues, pothole_issue, streetlight_issue


def box(x1, y1, x2, y2, confidence=0.8, label="pothole", category="pothole") -> Detection:
    return Detection(label=label, category=category, confidence=confidence, x1=x1, y1=y1, x2=x2, y2=y2)


def crack(x1, y1, x2, y2, label="longitudinal_crack", confidence=0.6) -> Detection:
    return box(x1, y1, x2, y2, confidence, label, "crack")


def light(confidence=0.7) -> Detection:
    return box(0.4, 0.1, 0.5, 0.6, confidence, "streetlight", "streetlight")


def test_the_app_never_imports_pytorch() -> None:
    import app.main  # noqa: F401

    assert "torch" not in sys.modules


# Potholes


def test_no_potholes_is_no_issue() -> None:
    assert pothole_issue([]) is None


def test_one_small_pothole_is_low() -> None:
    result = pothole_issue([box(0.4, 0.4, 0.5, 0.5)])  # 1% of the photo
    assert (result.severity, result.issue_type) == ("Low", "Pothole")


def test_two_potholes_are_at_least_medium() -> None:
    assert pothole_issue([box(0.1, 0.1, 0.15, 0.15), box(0.6, 0.6, 0.65, 0.65)]).severity == "Medium"


def test_three_potholes_are_high() -> None:
    result = pothole_issue([box(0.1, 0.1, 0.12, 0.12), box(0.5, 0.5, 0.52, 0.52), box(0.8, 0.8, 0.82, 0.82)])
    assert (result.severity, result.issue_type) == ("High", "Potholes")


def test_pothole_coverage_levels() -> None:
    assert pothole_issue([box(0.3, 0.3, 0.6, 0.5)]).severity == "Medium"  # 6%
    assert pothole_issue([box(0.1, 0.1, 0.6, 0.5)]).severity == "High"  # 20%
    assert pothole_issue([box(0.0, 0.2, 1.0, 0.7)]).severity == "Critical"  # 50%


def test_confidence_is_the_strongest_detection() -> None:
    assert pothole_issue([box(0, 0, 0.1, 0.1, 0.5), box(0.5, 0.5, 0.6, 0.6, 0.93)]).confidence == 0.93


def test_reason_mentions_camera_distance() -> None:
    assert "how close the photo was taken" in pothole_issue([box(0.4, 0.4, 0.5, 0.5)]).reason


# Cracks


def test_a_single_thin_crack_is_low() -> None:
    result = crack_issue([crack(0.4, 0.1, 0.45, 0.6)])
    assert (result.severity, result.issue_type, result.department) == ("Low", "Road cracks", "Roads and Stormwater")


def test_any_alligator_cracking_is_at_least_medium() -> None:
    assert crack_issue([crack(0.4, 0.4, 0.5, 0.5, "alligator_crack")]).severity == "Medium"


def test_widespread_alligator_cracking_is_high() -> None:
    assert crack_issue([crack(0.0, 0.5, 0.6, 1.0, "alligator_crack")]).severity == "High"  # 30%


def test_many_thin_cracks_are_medium() -> None:
    cracks = [crack(x, 0.1, x + 0.02, 0.3, "transverse_crack") for x in (0.1, 0.4, 0.7)]
    assert crack_issue(cracks).severity == "Medium"


# Streetlights


def test_a_visible_light_is_not_a_fault_on_its_own() -> None:
    assert streetlight_issue([light()], reported_out=False) is None


def test_a_reported_fault_with_a_visible_light() -> None:
    result = streetlight_issue([light(0.77)], reported_out=True)
    assert (result.issue_type, result.department, result.severity) == (
        "Streetlight not working", "Electricity (public lighting)", "Medium",
    )
    assert result.confidence == 0.77


def test_a_reported_fault_without_a_visible_light() -> None:
    result = streetlight_issue([], reported_out=True)
    assert result.confidence == 0.0
    assert "no streetlight was found" in result.reason


# Combining


def test_issues_are_sorted_most_severe_first() -> None:
    detections = [box(0.4, 0.4, 0.5, 0.5), crack(0.0, 0.5, 0.6, 1.0, "alligator_crack")]
    assert [i.category for i in find_issues(detections)] == ["crack", "pothole"]


def test_ties_keep_potholes_first() -> None:
    detections = [box(0.3, 0.3, 0.6, 0.5), crack(0.4, 0.4, 0.5, 0.5, "alligator_crack"), light()]
    assert [i.category for i in find_issues(detections, streetlight_out=True)] == ["pothole", "crack", "streetlight"]


def test_nothing_found_means_no_issues() -> None:
    assert find_issues([light()]) == []


# Detector helpers


def test_drop_contained_removes_a_box_inside_a_stronger_one() -> None:
    outer, inner = box(0.1, 0.1, 0.9, 0.9, 0.9), box(0.2, 0.2, 0.4, 0.4, 0.6)
    assert drop_contained([inner, outer]) == [outer]


def test_drop_contained_keeps_separate_boxes_and_different_labels() -> None:
    left, right = box(0.0, 0.0, 0.3, 0.3, 0.7), box(0.6, 0.6, 0.9, 0.9, 0.8)
    inside_crack = crack(0.65, 0.65, 0.8, 0.8)
    assert drop_contained([left, right, inside_crack]) == [right, left, inside_crack]


def test_resize_bilinear_keeps_flat_colour_and_shape() -> None:
    flat = np.full((37, 53, 3), 0.25, dtype=np.float32)
    out = resize_bilinear(flat, 20, 30)
    assert out.shape == (20, 30, 3)
    assert np.allclose(out, 0.25)


def test_resize_bilinear_matches_known_values() -> None:
    # 2x2 to 4x4 with half-pixel centres, as torch.nn.functional.interpolate computes it.
    pixels = np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32)[:, :, None]
    expected_row0 = [0.0, 0.25, 0.75, 1.0]
    assert np.allclose(resize_bilinear(pixels, 4, 4)[0, :, 0], expected_row0)
