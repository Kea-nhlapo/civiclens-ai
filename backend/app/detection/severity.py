"""Turn detections into an issue type, a severity and a plain explanation.

The model only says where potholes are. Severity is a rule on top of that, using
two things a photo can show: how many potholes there are, and how much of the
photo they cover. Coverage depends on how close the camera was, so it is a rough
proxy for size, not a measurement, and the explanation says so.
"""

from dataclasses import dataclass

from app.detection.detector import Detection
from app.models.schemas import Severity

CRITICAL_COVERAGE = 0.40
HIGH_COVERAGE = 0.15
MEDIUM_COVERAGE = 0.05
HIGH_COUNT = 3


@dataclass(frozen=True)
class Assessment:
    issue_type: str
    severity: Severity
    confidence: float
    pothole_count: int
    coverage: float
    reason: str


def coverage_of(detections: list[Detection]) -> float:
    # Boxes rarely overlap after drop_contained, so a plain sum is close enough
    # and stays easy to explain. Capped at the whole photo.
    return min(1.0, sum(d.area for d in detections))


def assess(detections: list[Detection]) -> Assessment:
    count = len(detections)
    if count == 0:
        return Assessment(
            issue_type="No pothole detected",
            severity="Low",
            confidence=0.0,
            pothole_count=0,
            coverage=0.0,
            reason="The detector found no potholes in this photo.",
        )

    coverage = coverage_of(detections)
    confidence = max(d.confidence for d in detections)
    percent = f"{coverage:.0%}" if coverage >= 0.01 else "under 1%"
    holes = "1 pothole" if count == 1 else f"{count} potholes"

    if coverage >= CRITICAL_COVERAGE:
        severity: Severity = "Critical"
        why = f"{holes} covering {percent} of the photo, which points to a large area of failed road surface."
    elif coverage >= HIGH_COVERAGE or count >= HIGH_COUNT:
        severity = "High"
        why = (
            f"{holes} covering {percent} of the photo."
            if coverage >= HIGH_COVERAGE
            else f"{holes} close together, covering {percent} of the photo."
        )
    elif coverage >= MEDIUM_COVERAGE or count == 2:
        severity = "Medium"
        why = f"{holes} covering {percent} of the photo."
    else:
        severity = "Low"
        why = f"{holes} covering {percent} of the photo, so it looks small or far from the camera."

    return Assessment(
        issue_type="Pothole" if count == 1 else "Potholes",
        severity=severity,
        confidence=round(confidence, 2),
        pothole_count=count,
        coverage=round(coverage, 4),
        reason=why + " Coverage depends on how close the photo was taken, so an inspector should confirm the size.",
    )
