import asyncio
from io import BytesIO

import httpx
from PIL import Image

from app.main import app


async def request(path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, **kwargs)


def image_bytes() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (20, 20), "gray").save(stream, format="JPEG")
    return stream.getvalue()


def test_analyze_report_uses_fallback_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = asyncio.run(request(
        "/api/analyze-report",
        files={"image": ("road.jpg", image_bytes(), "image/jpeg")},
        data={"location": "Main Road", "notes": "Deep hole near the crossing"},
    ))
    assert response.status_code == 200
    payload = response.json()
    assert payload["issue_type"] == "Pothole"
    assert payload["severity"] == "High"
    assert payload["municipal_report"]["location"] == "Main Road"
    assert "draft" in payload["citizen_message"].lower()
    assert len(payload["next_steps"]) == 4


def test_rejects_invalid_image() -> None:
    response = asyncio.run(request(
        "/api/analyze-report",
        files={"image": ("not-image.txt", b"not an image", "text/plain")},
    ))
    assert response.status_code == 400
