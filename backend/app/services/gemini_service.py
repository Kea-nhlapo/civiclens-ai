"""Optional: let Gemini word the report more naturally.

The detector decides what is in the photo. Gemini only rewrites the text around
those facts, and never changes the issue type, severity, confidence or boxes.
Without GEMINI_API_KEY, or if the call fails, the detector's own report is used.
"""

import logging
import os

from google import genai
from google.genai import types

from app.models.schemas import AnalysisReport, ReportWording

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You help a citizen word a municipal pothole report. An object detector has already
analysed the attached photo. Treat its findings below as fixed facts: do not change the number of
potholes, the severity, or the confidence, and do not add hazards, measurements or locations that are
not in the facts or the photo. Write plainly and briefly for a South African municipal roads department.
Never claim the report was submitted; it is a draft the citizen reviews and submits themselves.
Return strict JSON matching the schema."""


def reword_with_gemini(
    report: AnalysisReport, image: bytes, mime_type: str, location: str | None, notes: str | None
) -> AnalysisReport:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or report.pothole_count == 0:
        return report

    facts = (
        f"Detector findings: {report.pothole_count} pothole(s), severity {report.severity}, "
        f"highest confidence {report.confidence:.0%}, covering about {report.coverage:.0%} of the photo.\n"
        f"Why that severity: {report.severity_reason}\n"
        f"Citizen location: {location or 'not provided'}\n"
        f"Citizen notes: {notes or 'not provided'}\n"
        f"Current draft title: {report.municipal_report.title}\n"
        f"Current draft description: {report.municipal_report.description}"
    )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            contents=[
                types.Part.from_text(text=SYSTEM_PROMPT + "\n\n" + facts),
                types.Part.from_bytes(data=image, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReportWording,
                temperature=0.2,
            ),
        )
        wording = ReportWording.model_validate_json(response.text or "")
    except Exception as exc:  # Gemini, network and schema errors all fall back to the detector's text.
        logger.warning("Gemini wording unavailable; using detector report (%s)", type(exc).__name__)
        return report

    municipal = report.municipal_report.model_copy(
        update={"title": wording.title, "description": wording.description, "evidence_notes": wording.evidence_notes}
    )
    return report.model_copy(
        update={
            "summary": wording.summary,
            "recommended_action": wording.recommended_action,
            "municipal_report": municipal,
            "citizen_message": wording.citizen_message,
            "next_steps": wording.next_steps or report.next_steps,
            "analysis_source": "detector+gemini",
        }
    )
