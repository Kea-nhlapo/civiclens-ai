"""Build the report from what the detector actually found.

This is the report every request gets. When Gemini is configured it may reword the
text afterwards, but the facts here (issue type, severity, confidence, the boxes)
always come from the detector.
"""

from app.detection.detector import DetectionResult
from app.detection.severity import Assessment
from app.models.schemas import AnalysisReport, DetectionBox, MunicipalReport, Severity

ROADS_DEPARTMENT = "Roads and Stormwater"
NO_DEPARTMENT = "No roads report needed"

ACTIONS: dict[Severity, str] = {
    "Critical": "Inspect urgently, mark or barricade the area, and schedule a repair as soon as possible.",
    "High": "Inspect soon and schedule a repair. Mark the hazard if the repair cannot happen quickly.",
    "Medium": "Add the site to the next road maintenance round and monitor it until it is repaired.",
    "Low": "Log the site for routine road maintenance.",
}


def _place(location: str | None) -> str:
    return location.strip() if location and location.strip() else "Location to be confirmed by the citizen"


def _boxes(result: DetectionResult) -> list[DetectionBox]:
    return [DetectionBox(**vars(d)) for d in result.detections]


def build_report(
    result: DetectionResult, assessment: Assessment, location: str | None, notes: str | None
) -> AnalysisReport:
    place = _place(location)
    citizen_note = notes.strip() if notes and notes.strip() else ""
    shared = dict(
        detections=_boxes(result),
        pothole_count=assessment.pothole_count,
        coverage=assessment.coverage,
        severity_reason=assessment.reason,
        image_width=result.image_width,
        image_height=result.image_height,
        model=result.model,
        analysis_source="detector",
    )

    if assessment.pothole_count == 0:
        return AnalysisReport(
            issue_type=assessment.issue_type,
            severity="Low",
            confidence=0.0,
            summary=(
                "No pothole was detected in this photo. CivicLens can only detect potholes, so other problems "
                "such as broken streetlights or blocked drains are not checked."
            ),
            responsible_department=NO_DEPARTMENT,
            recommended_action="If there is a pothole, retake the photo closer to it, in daylight, with the road surface filling most of the frame.",
            municipal_report=MunicipalReport(
                title="No pothole detected",
                description=(
                    "The pothole detector did not find road damage in the attached photo, so no road repair report "
                    "has been drafted. If you can see a pothole, retake the photo and try again."
                ),
                location=place,
                evidence_notes=citizen_note or "No detections above the confidence threshold.",
                priority="Low",
                suggested_department=NO_DEPARTMENT,
            ),
            citizen_message="No pothole found in this photo. Try a closer, clearer photo if you can see one.",
            next_steps=[
                "Retake the photo closer to the damage",
                "Make sure the road surface fills most of the frame",
                "Report other kinds of problems directly to your municipality",
            ],
            **shared,
        )

    holes = "a pothole" if assessment.pothole_count == 1 else f"{assessment.pothole_count} potholes"
    summary = (
        f"The detector found {holes} with up to {assessment.confidence:.0%} confidence. "
        f"Severity is {assessment.severity}: {assessment.reason}"
    )
    evidence = (
        f"Automated detection: {holes}, highest confidence {assessment.confidence:.0%}, "
        f"covering about {assessment.coverage:.0%} of the photo."
    )
    if citizen_note:
        evidence += f" Citizen note: {citizen_note}"

    return AnalysisReport(
        issue_type=assessment.issue_type,
        severity=assessment.severity,
        confidence=assessment.confidence,
        summary=summary,
        responsible_department=ROADS_DEPARTMENT,
        recommended_action=ACTIONS[assessment.severity],
        municipal_report=MunicipalReport(
            title=f"{assessment.severity} priority: {holes} reported",
            description=(
                f"A citizen photo shows {holes} on a public road at {place}. "
                f"{assessment.reason} Please inspect the site and schedule a repair. "
                "This draft was generated automatically and should be checked before it is submitted."
            ),
            location=place,
            evidence_notes=evidence,
            priority=assessment.severity,
            suggested_department=ROADS_DEPARTMENT,
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
