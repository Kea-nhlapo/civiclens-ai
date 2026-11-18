"""Build the report from what the detectors actually found.

This is the report every request gets. When Gemini is configured it may reword the
text afterwards, but the facts here (issue types, severities, confidences, the
boxes) always come from the detectors.

The most severe issue leads: it sets the issue type, department and priority. Any
other issues in the same photo are listed in the description so nothing is lost.
"""

from app.detection.detector import DetectionResult
from app.detection.issues import Issue
from app.models.schemas import AnalysisReport, DetectionBox, IssueSummary, MunicipalReport, Severity

NO_DEPARTMENT = "No report needed"

ACTIONS: dict[str, dict[Severity, str]] = {
    "pothole": {
        "Critical": "Inspect urgently, mark or barricade the area, and schedule a repair as soon as possible.",
        "High": "Inspect soon and schedule a repair. Mark the hazard if the repair cannot happen quickly.",
        "Medium": "Add the site to the next road maintenance round and monitor it until it is repaired.",
        "Low": "Log the site for routine road maintenance.",
    },
    "crack": {
        "High": "Inspect the road base and plan resurfacing before the cracking turns into potholes.",
        "Medium": "Seal the cracks in the next maintenance round to keep water out of the road base.",
        "Low": "Log the crack for routine crack sealing.",
    },
    "streetlight": {
        "Medium": "Send a lighting technician to check the lamp, its wiring and its supply.",
    },
}


def _place(location: str | None) -> str:
    return location.strip() if location and location.strip() else "Location to be confirmed by the citizen"


def _what(issue: Issue) -> str:
    if issue.category == "pothole":
        return "a pothole" if issue.count == 1 else f"{issue.count} potholes"
    if issue.category == "crack":
        return "road cracking"
    return "a streetlight that is not working"


def _evidence(issue: Issue) -> str:
    if issue.category == "streetlight":
        seen = (
            f"streetlight visible in the photo (highest confidence {issue.confidence:.0%})"
            if issue.count
            else "no streetlight visible in the photo"
        )
        return f"Fault reported by the citizen; {seen}"
    return (
        f"Automated detection: {_what(issue)}, highest confidence {issue.confidence:.0%}, "
        f"covering about {issue.coverage:.0%} of the photo"
    )


def _summary_of(issue: Issue) -> IssueSummary:
    return IssueSummary(**vars(issue))


def _no_issue_report(result: DetectionResult, place: str, note: str, shared: dict) -> AnalysisReport:
    lights = len(result.of("streetlight"))
    seen = (
        f" The photo shows {'a streetlight' if lights == 1 else f'{lights} streetlights'}. "
        "If one isn't working, tick \"This streetlight is not working\" and send the photo again."
        if lights
        else ""
    )
    return AnalysisReport(
        issue_type="No issue detected",
        severity="Low",
        confidence=0.0,
        summary=(
            "No potholes or road cracks were detected in this photo." + seen + " CivicLens can't detect "
            "other problems, such as blocked drains or illegal dumping, yet."
        ),
        responsible_department=NO_DEPARTMENT,
        recommended_action="If there is road damage, retake the photo closer to it, in daylight, with the road surface filling most of the frame.",
        municipal_report=MunicipalReport(
            title="No issue detected",
            description=(
                "The detectors did not find road damage in the attached photo, so no report has been drafted. "
                "If you can see a problem, retake the photo and try again."
            ),
            location=place,
            evidence_notes=note or "No detections above the confidence thresholds.",
            priority="Low",
            suggested_department=NO_DEPARTMENT,
        ),
        citizen_message="Nothing to report was found in this photo. Try a closer, clearer photo if you can see a problem.",
        next_steps=[
            "Retake the photo closer to the problem",
            "For road damage, make sure the road fills most of the frame",
            "Report other kinds of problems directly to your municipality",
        ],
        **shared,
    )


def build_report(
    result: DetectionResult, issues: list[Issue], location: str | None, notes: str | None
) -> AnalysisReport:
    place = _place(location)
    note = notes.strip() if notes and notes.strip() else ""
    lead = issues[0] if issues else None
    potholes = next((i for i in issues if i.category == "pothole"), None)
    shared = dict(
        detections=[DetectionBox(**vars(d)) for d in result.detections],
        issues=[_summary_of(i) for i in issues],
        pothole_count=potholes.count if potholes else 0,
        coverage=lead.coverage if lead else 0.0,
        severity_reason=lead.reason if lead else "",
        image_width=result.image_width,
        image_height=result.image_height,
        models=list(result.models),
        analysis_source="detector",
    )
    if lead is None:
        return _no_issue_report(result, place, note, shared)

    others = issues[1:]
    also = ""
    if others:
        listed = "; ".join(f"{_what(i)} ({i.severity.lower()} priority, {i.department})" for i in others)
        also = f" The same photo also shows {listed}."

    where = f"at {location.strip()}" if location and location.strip() else "at a location the citizen still needs to confirm"
    if lead.category == "streetlight":
        found = "A citizen reports a streetlight that is not working."
    else:
        found = f"The detector found {_what(lead)} with up to {lead.confidence:.0%} confidence."
    summary = f"{found} Severity is {lead.severity}: {lead.reason}{also}"

    evidence = "; ".join(_evidence(i) for i in issues) + "."
    if note:
        evidence += f" Citizen note: {note}"

    return AnalysisReport(
        issue_type=lead.issue_type,
        severity=lead.severity,
        confidence=lead.confidence,
        summary=summary,
        responsible_department=lead.department,
        recommended_action=ACTIONS[lead.category][lead.severity],
        municipal_report=MunicipalReport(
            title=f"{lead.severity} priority: {lead.issue_type.lower()} reported",
            description=(
                f"A citizen photo shows {_what(lead)} {where}. {lead.reason}{also} "
                "Please inspect the site. This draft was generated automatically and should be checked before it is submitted."
            ),
            location=place,
            evidence_notes=evidence,
            priority=lead.severity,
            suggested_department=lead.department,
        ),
        citizen_message="Your draft report is ready. Check the location and details, then submit it to your municipality yourself.",
        next_steps=[
            "Confirm the exact location",
            "Attach the photo",
            "Submit through your municipality's official channel",
            "Keep the reference number you receive",
        ],
        **shared,
    )
