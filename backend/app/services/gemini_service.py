import logging
import os

from google import genai
from google.genai import types

from app.models.schemas import AnalysisReport
from app.services.report_service import fallback_report

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are CivicLens AI, an assistant that drafts municipal infrastructure reports.
Analyze the supplied civic-issue photo and citizen context. Classify the issue, estimate severity,
identify the most likely municipal department, recommend a practical action, and draft a concise,
professional report. Return strict JSON matching the supplied schema only. Never make legal claims,
claim certainty beyond the visible evidence, or claim that a report was submitted. Explicitly state
that the output is a draft that the citizen must review and submit manually. Severity must be exactly
Low, Medium, High, or Critical. Confidence must be between 0 and 1.

Do not force the image into a known civic-issue category. First determine whether the image actually
shows a public infrastructure or public-space maintenance problem. If it does not, set issue_type to
"Not a civic infrastructure issue", use Low severity, select "No municipal department recommended",
and clearly explain what is visible and why no civic report should be submitted. If the image is too
blurry, dark, obstructed, or ambiguous to classify reliably, set issue_type to "Unable to classify",
use Low severity, keep confidence appropriately low, and request a clearer photo. Base every field on
visible evidence and the supplied context; do not invent objects, damage, locations, or hazards.
"""


def analyze_with_gemini(image: bytes, mime_type: str, location: str | None, notes: str | None) -> AnalysisReport:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return fallback_report(location, notes)

    context = f"Citizen location: {location or 'not provided'}\nCitizen notes: {notes or 'not provided'}"
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            contents=[
                types.Part.from_text(text=SYSTEM_PROMPT + "\n" + context),
                types.Part.from_bytes(data=image, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalysisReport,
                temperature=0.2,
            ),
        )
        return AnalysisReport.model_validate_json(response.text or "")
    except Exception as exc:  # Gemini/network/schema errors all degrade safely for demo continuity.
        logger.warning("Gemini analysis unavailable; using fallback (%s)", type(exc).__name__)
        return fallback_report(location, notes)
