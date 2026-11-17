from app.detection.detector import Detection, drop_contained
from app.detection.severity import assess


def box(x1: float, y1: float, x2: float, y2: float, confidence: float = 0.8) -> Detection:
    return Detection(label="pothole", confidence=confidence, x1=x1, y1=y1, x2=x2, y2=y2)


def test_no_detections_is_low_with_zero_confidence() -> None:
    result = assess([])
    assert (result.issue_type, result.severity, result.confidence, result.pothole_count) == (
        "No pothole detected", "Low", 0.0, 0,
    )


def test_one_small_pothole_is_low() -> None:
    result = assess([box(0.4, 0.4, 0.5, 0.5)])  # 1% of the photo
    assert result.severity == "Low"
    assert result.issue_type == "Pothole"


def test_two_potholes_are_at_least_medium() -> None:
    assert assess([box(0.1, 0.1, 0.15, 0.15), box(0.6, 0.6, 0.65, 0.65)]).severity == "Medium"


def test_medium_coverage() -> None:
    assert assess([box(0.3, 0.3, 0.6, 0.5)]).severity == "Medium"  # 6%


def test_three_potholes_are_high() -> None:
    result = assess([box(0.1, 0.1, 0.12, 0.12), box(0.5, 0.5, 0.52, 0.52), box(0.8, 0.8, 0.82, 0.82)])
    assert result.severity == "High"
    assert result.issue_type == "Potholes"


def test_high_coverage() -> None:
    assert assess([box(0.1, 0.1, 0.6, 0.5)]).severity == "High"  # 20%


def test_critical_coverage() -> None:
    assert assess([box(0.0, 0.2, 1.0, 0.7)]).severity == "Critical"  # 50%


def test_confidence_is_the_strongest_detection() -> None:
    assert assess([box(0, 0, 0.1, 0.1, 0.5), box(0.5, 0.5, 0.6, 0.6, 0.93)]).confidence == 0.93


def test_reason_mentions_camera_distance() -> None:
    assert "how close the photo was taken" in assess([box(0.4, 0.4, 0.5, 0.5)]).reason


def test_drop_contained_removes_a_box_inside_a_stronger_one() -> None:
    outer = box(0.1, 0.1, 0.9, 0.9, 0.9)
    inner = box(0.2, 0.2, 0.4, 0.4, 0.6)
    assert drop_contained([inner, outer]) == [outer]


def test_drop_contained_keeps_separate_potholes() -> None:
    left, right = box(0.0, 0.0, 0.3, 0.3, 0.7), box(0.6, 0.6, 0.9, 0.9, 0.8)
    assert drop_contained([left, right]) == [right, left]
