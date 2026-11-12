import asyncio
from pathlib import Path

import httpx
import pytest

from app.main import app

SAMPLES = Path(__file__).parent / "samples"


async def request(path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, **kwargs)


def analyze(name: str, **data: str) -> dict:
    response = asyncio.run(request(
        "/api/analyze-report",
        files={"image": (name, (SAMPLES / name).read_bytes(), "image/jpeg")},
        data=data,
    ))
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(autouse=True)
def no_gemini(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.mark.parametrize(
    ("name", "count", "severity"),
    [
        ("pothole-single.jpg", 1, "Low"),
        ("pothole-close.jpg", 1, "Medium"),
        ("pothole-cluster.jpg", 4, "High"),
        ("pothole-large.jpg", 1, "High"),
    ],
)
def test_detects_potholes_in_real_photos(name: str, count: int, severity: str) -> None:
    report = analyze(name, location="Main Road", notes="Near the crossing")
    assert report["pothole_count"] == count
    assert len(report["detections"]) == count
    assert report["severity"] == severity
    assert report["municipal_report"]["priority"] == severity
    assert report["issue_type"] in {"Pothole", "Potholes"}
    assert report["responsible_department"] == "Roads and Stormwater"
    assert report["analysis_source"] == "detector"
    assert report["model"] == "pothole_rfdetr_nano_v4_r1"
    for box in report["detections"]:
        assert box["label"] == "pothole"
        assert box["confidence"] >= 0.45
        assert 0 <= box["x1"] < box["x2"] <= 1
        assert 0 <= box["y1"] < box["y2"] <= 1
    assert report["confidence"] == round(max(b["confidence"] for b in report["detections"]), 2)
    assert report["municipal_report"]["location"] == "Main Road"
    assert "Near the crossing" in report["municipal_report"]["evidence_notes"]


@pytest.mark.parametrize("name", ["road-clean-desert.jpg", "road-clean-suburb.jpg"])
def test_finds_nothing_on_undamaged_roads(name: str) -> None:
    report = analyze(name)
    assert report["pothole_count"] == 0
    assert report["detections"] == []
    assert report["issue_type"] == "No pothole detected"
    assert report["severity"] == "Low"
    assert report["confidence"] == 0.0


def test_reports_original_image_size() -> None:
    report = analyze("pothole-close.jpg")
    assert (report["image_width"], report["image_height"]) == (480, 640)


def test_rejects_invalid_image() -> None:
    response = asyncio.run(request(
        "/api/analyze-report",
        files={"image": ("not-image.txt", b"not an image", "text/plain")},
    ))
    assert response.status_code == 400
