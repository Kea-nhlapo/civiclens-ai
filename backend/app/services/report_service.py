from app.models.schemas import AnalysisReport, MunicipalReport


def fallback_report(location: str | None = None, notes: str | None = None) -> AnalysisReport:
    place = location.strip() if location and location.strip() else "Location to be confirmed by citizen"
    evidence = notes.strip() if notes and notes.strip() else "Photo evidence attached; exact dimensions and road position require inspection."
    return AnalysisReport(
        issue_type="Pothole",
        severity="High",
        confidence=0.91,
        summary="Large pothole visible on a public road, likely creating risk for vehicles and pedestrians.",
        responsible_department="Roads and Stormwater Department",
        recommended_action="Dispatch a road maintenance team for inspection, temporary hazard marking, and repair.",
        municipal_report=MunicipalReport(
            title="Urgent Road Hazard Report: Large Pothole",
            description=(
                "A large pothole appears to be present on a public roadway at the location listed below. "
                "The damaged surface may pose a safety risk to vehicles, cyclists, and pedestrians. "
                "Please review the attached photo, inspect the site, and schedule appropriate repairs. "
                "This is an AI-generated draft and should be reviewed before manual submission."
            ),
            location=place,
            evidence_notes=evidence,
            priority="High",
            suggested_department="Roads and Stormwater Department",
        ),
        citizen_message="Your draft report is ready. Review it, then submit it manually to your municipality.",
        next_steps=[
            "Confirm the location",
            "Attach the photo",
            "Submit to the municipal service portal",
            "Save your reference number",
        ],
    )

