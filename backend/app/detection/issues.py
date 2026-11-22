"""Turn detections into reportable issues, each with a department and a severity.

The models only say where things are. Everything here is a plain rule on top,
using what a single photo can show: how many there are and how much of the photo
they cover. Coverage depends on how close the camera was, so it is a rough proxy
for size, and every reason says so.

A photo can show more than one problem. Each category becomes its own issue, and
the most severe one leads the report.
"""

from dataclasses import dataclass

from app.detection.detector import Detection
from app.models.schemas import Severity

ROADS = "Roads and Stormwater"
LIGHTING = "Electricity (public lighting)"
WASTE = "Waste Management (Solid Waste)"
SEVERITY_ORDER: dict[Severity, int] = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
CAVEAT = " Coverage depends on how close the photo was taken, so an inspector should confirm the size."

CRITICAL_COVERAGE = 0.40
HIGH_COVERAGE = 0.15
MEDIUM_COVERAGE = 0.05
HIGH_COUNT = 3
# Dumping photos are usually framed tightly on the pile, and OWLv2's boxes are
# generous, so a much larger share of the photo is needed before it counts as large.
DUMPING_HIGH_COVERAGE = 0.40
CRACK_NAMES = {
    "longitudinal_crack": "lengthwise crack",
    "transverse_crack": "crosswise crack",
    "alligator_crack": "alligator (fatigue) cracking",
}


@dataclass(frozen=True)
class Issue:
    category: str
    issue_type: str
    department: str
    severity: Severity
    confidence: float
    count: int
    coverage: float
    reason: str


def coverage_of(detections: list[Detection]) -> float:
    # Same-label duplicates are already dropped, so a plain sum is close enough and
    # stays easy to explain. Capped at the whole photo.
    return min(1.0, sum(d.area for d in detections))


def _percent(coverage: float) -> str:
    return f"{coverage:.0%}" if coverage >= 0.01 else "under 1%"


def _plural(count: int, noun: str) -> str:
    return f"1 {noun}" if count == 1 else f"{count} {noun}s"


def pothole_issue(potholes: list[Detection]) -> Issue | None:
    if not potholes:
        return None
    count, coverage = len(potholes), coverage_of(potholes)
    holes, percent = _plural(count, "pothole"), _percent(coverage)
    if coverage >= CRITICAL_COVERAGE:
        severity: Severity = "Critical"
        why = f"{holes} covering {percent} of the photo, which points to a large area of failed road surface."
    elif coverage >= HIGH_COVERAGE or count >= HIGH_COUNT:
        severity = "High"
        why = f"{holes} covering {percent} of the photo." if coverage >= HIGH_COVERAGE else f"{holes} close together, covering {percent} of the photo."
    elif coverage >= MEDIUM_COVERAGE or count == 2:
        severity = "Medium"
        why = f"{holes} covering {percent} of the photo."
    else:
        severity = "Low"
        why = f"{holes} covering {percent} of the photo, so it looks small or far from the camera."
    return Issue(
        category="pothole",
        issue_type="Pothole" if count == 1 else "Potholes",
        department=ROADS,
        severity=severity,
        confidence=round(max(d.confidence for d in potholes), 2),
        count=count,
        coverage=round(coverage, 4),
        reason=why + CAVEAT,
    )


def crack_issue(cracks: list[Detection]) -> Issue | None:
    """Alligator cracking means the layers under the surface are failing, so it ranks
    above single lengthwise or crosswise cracks, which usually only need sealing."""
    if not cracks:
        return None
    count, coverage = len(cracks), coverage_of(cracks)
    alligator = [d for d in cracks if d.label == "alligator_crack"]
    kinds = sorted({CRACK_NAMES[d.label] for d in cracks})
    found = f"{_plural(count, 'crack area')} ({', '.join(kinds)}) covering {_percent(coverage)} of the photo"
    if alligator and (coverage >= HIGH_COVERAGE or len(alligator) >= HIGH_COUNT):
        severity: Severity = "High"
        why = f"{found}. Widespread alligator cracking usually means the road base is failing and potholes will follow."
    elif alligator or coverage >= HIGH_COVERAGE or count >= HIGH_COUNT:
        severity = "Medium"
        why = f"{found}. Left alone, cracks let water in and turn into potholes."
    else:
        severity = "Low"
        why = f"{found}. A crack like this usually needs sealing rather than urgent repair."
    return Issue(
        category="crack",
        issue_type="Road cracks",
        department=ROADS,
        severity=severity,
        confidence=round(max(d.confidence for d in cracks), 2),
        count=count,
        coverage=round(coverage, 4),
        reason=why + CAVEAT,
    )


def streetlight_issue(lights: list[Detection], reported_out: bool) -> Issue | None:
    """A photo can show a streetlight but not whether it works: in daylight every
    lamp is off. So a fault is only reported when the citizen says the light is out;
    the detector then confirms there is a streetlight in the photo."""
    if not reported_out:
        return None
    if lights:
        why = (
            f"You reported that the light is not working, and the detector found {_plural(len(lights), 'streetlight')} "
            "in the photo. The photo cannot show whether a light works, so the fault itself comes from your report."
        )
        confidence = round(max(d.confidence for d in lights), 2)
    else:
        why = (
            "You reported that a streetlight is not working, but no streetlight was found in the photo. "
            "A clearer photo of the pole and lamp will help the municipality find it."
        )
        confidence = 0.0
    return Issue(
        category="streetlight",
        issue_type="Streetlight not working",
        department=LIGHTING,
        severity="Medium",
        confidence=confidence,
        count=len(lights),
        coverage=round(coverage_of(lights), 4),
        reason=why,
    )


def dumping_issue(piles: list[Detection]) -> Issue | None:
    """Dumped waste attracts more dumping, blocks pavements and drains, and can be a
    health hazard, so any dumping is at least Medium. The detector is zero-shot and
    makes more mistakes than the others, and the reason says so."""
    if not piles:
        return None
    count, coverage = len(piles), coverage_of(piles)
    found = f"{_plural(count, 'area')} of dumped waste covering {_percent(coverage)} of the photo"
    if coverage >= DUMPING_HIGH_COVERAGE or count >= HIGH_COUNT:
        severity: Severity = "High"
        why = f"{found}, which looks like a large dump that needs a removal team."
    else:
        severity = "Medium"
        why = f"{found}. Left alone, dumped waste tends to attract more dumping."
    return Issue(
        category="dumping",
        issue_type="Illegal dumping",
        department=WASTE,
        severity=severity,
        confidence=round(max(d.confidence for d in piles), 2),
        count=count,
        coverage=round(coverage, 4),
        reason=why + " This detector matches the photo against text descriptions, so it is less certain than the others; please check the photo.",
    )


def find_issues(detections: list[Detection], streetlight_out: bool = False) -> list[Issue]:
    by_category = lambda c: [d for d in detections if d.category == c]  # noqa: E731
    issues = [
        pothole_issue(by_category("pothole")),
        crack_issue(by_category("crack")),
        streetlight_issue(by_category("streetlight"), streetlight_out),
        dumping_issue(by_category("dumping")),
    ]
    found = [i for i in issues if i is not None]
    # Most severe first; on a tie keep the order above (potholes, cracks, lights, dumping).
    return sorted(found, key=lambda i: -SEVERITY_ORDER[i.severity])
