from app.models.schemas import AnalysisReport, MunicipalReport


def fallback_report(location: str | None = None, notes: str | None = None) -> AnalysisReport:
    place = location.strip() if location and location.strip() else "Location to be confirmed by citizen"
    evidence = notes.strip() if notes and notes.strip() else "Photo evidence attached; exact dimensions and road position require inspection."
    return AnalysisReport(
        issue_type="Analysis unavailable",
        severity="Low",
        confidence=0.0,
        summary="The image could not be analyzed by Gemini. No civic issue classification has been inferred.",
        responsible_department="To be determined after manual review",
        recommended_action="Review the photo manually and retry once AI analysis is available.",
        municipal_report=MunicipalReport(
            title="Draft Civic Issue Report: Manual Review Required",
            description=(
                "Automated image analysis was unavailable, so the type and severity of this issue could not be verified. "
                "Please review the attached photo and citizen notes manually before choosing a department or submitting. "
                "This draft does not claim that a civic infrastructure problem was detected."
            ),
            location=place,
            evidence_notes=evidence,
            priority="Low",
            suggested_department="To be determined after manual review",
        ),
        citizen_message="AI analysis is unavailable. Review the image manually or retry before submitting anything.",
        next_steps=[
            "Confirm that Gemini is configured",
            "Retry the image analysis",
            "Review the photo and notes manually",
            "Only submit after confirming the issue",
        ],
    )
