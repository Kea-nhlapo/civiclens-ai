from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def image_bytes() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (20, 20), "gray").save(stream, format="JPEG")
    return stream.getvalue()


def test_analyze_report_uses_fallback_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/api/analyze-report",
        files={"image": ("road.jpg", image_bytes(), "image/jpeg")},
        data={"location": "Main Road", "notes": "Deep hole near the crossing"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["issue_type"] == "Pothole"
    assert payload["severity"] == "High"
    assert payload["municipal_report"]["location"] == "Main Road"
    assert "draft" in payload["citizen_message"].lower()
    assert len(payload["next_steps"]) == 4


def test_rejects_invalid_image() -> None:
    response = client.post(
        "/api/analyze-report",
        files={"image": ("not-image.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400

