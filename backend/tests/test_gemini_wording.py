from types import SimpleNamespace

from app.detection.detector import Detection, DetectionResult
from app.detection.issues import find_issues
from app.models.schemas import ReportWording
from app.services import gemini_service
from app.services.report_service import build_report


def detector_report():
    detections = [Detection(label="pothole", category="pothole", confidence=0.88, x1=0.2, y1=0.3, x2=0.6, y2=0.7)]
    result = DetectionResult(detections=detections, image_width=640, image_height=480)
    return build_report(result, find_issues(detections), "Main Road", None)


class FakeClient:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text, self.error = text, error
        self.models = self

    def generate_content(self, **_):
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text)


WORDING = ReportWording(
    summary="Reworded summary",
    recommended_action="Reworded action",
    title="Reworded title",
    description="Reworded description",
    evidence_notes="Reworded evidence",
    citizen_message="Reworded message",
    next_steps=["One", "Two"],
)


def test_without_a_key_the_detector_report_is_returned(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    report = detector_report()
    assert gemini_service.reword_with_gemini(report, b"", "image/jpeg", None, None) is report


def test_gemini_rewords_text_but_keeps_the_detector_facts(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_service.genai, "Client", lambda api_key: FakeClient(WORDING.model_dump_json()))
    original = detector_report()
    reworded = gemini_service.reword_with_gemini(original, b"", "image/jpeg", "Main Road", None)

    assert reworded.analysis_source == "detector+gemini"
    assert reworded.summary == "Reworded summary"
    assert reworded.municipal_report.title == "Reworded title"
    for field in ("issue_type", "severity", "confidence", "pothole_count", "coverage", "detections", "issues", "responsible_department"):
        assert getattr(reworded, field) == getattr(original, field)
    assert reworded.municipal_report.priority == original.municipal_report.priority
    assert reworded.municipal_report.location == "Main Road"


def test_gemini_failure_falls_back_to_the_detector_report(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_service.genai, "Client", lambda api_key: FakeClient(error=TimeoutError()))
    report = detector_report()
    assert gemini_service.reword_with_gemini(report, b"", "image/jpeg", None, None) is report
