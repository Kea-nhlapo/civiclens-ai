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


def categories(report: dict) -> set[str]:
    return {d["category"] for d in report["detections"]}


def issue(report: dict, category: str) -> dict | None:
    return next((i for i in report["issues"] if i["category"] == category), None)



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
    potholes = issue(report, "pothole")
    assert potholes["count"] == report["pothole_count"] == count
    assert potholes["severity"] == severity
    assert potholes["department"] == "Roads and Stormwater"
    assert len([d for d in report["detections"] if d["category"] == "pothole"]) == count
    assert report["analysis_source"] == "detector"
    assert report["models"] == [
        "pothole_rfdetr_nano_v4_r1", "rdd2022_rfdetr_small", "dfine_small_obj365", "owlv2_base_dumping_672",
    ]
    for box in report["detections"]:
        assert 0 <= box["x1"] < box["x2"] <= 1
        assert 0 <= box["y1"] < box["y2"] <= 1
    assert report["municipal_report"]["location"] == "Main Road"
    assert "Near the crossing" in report["municipal_report"]["evidence_notes"]


def test_the_most_severe_issue_leads_the_report() -> None:
    # A small pothole inside a wide patch of alligator cracking: the cracking rates
    # higher, so it leads, and the pothole is still listed.
    report = analyze("pothole-single.jpg")
    assert [i["category"] for i in report["issues"]] == ["crack", "pothole"]
    assert report["issue_type"] == "Road cracks"
    assert report["severity"] == report["municipal_report"]["priority"] == "High"
    assert "also shows a pothole" in report["summary"]


@pytest.mark.parametrize(("name", "label"), [("crack-lengthwise.jpg", "longitudinal_crack"), ("crack-suburb.jpg", "alligator_crack")])
def test_detects_road_cracks(name: str, label: str) -> None:
    report = analyze(name)
    assert "pothole" not in categories(report)
    assert label in {d["label"] for d in report["detections"]}
    assert report["issue_type"] == "Road cracks"
    assert report["responsible_department"] == "Roads and Stormwater"


def test_alligator_cracking_ranks_above_a_single_lengthwise_crack() -> None:
    assert analyze("crack-suburb.jpg")["severity"] == "High"
    assert analyze("crack-lengthwise.jpg")["severity"] == "Low"


@pytest.mark.parametrize("name", ["streetlight-durban.jpg", "streetlight-night.jpg"])
def test_detects_streetlights_but_only_reports_a_fault_when_the_citizen_does(name: str) -> None:
    unreported = analyze(name)
    assert "streetlight" in categories(unreported)
    assert unreported["issues"] == []
    assert unreported["issue_type"] == "No issue detected"
    assert "not working" in unreported["summary"]

    reported = analyze(name, streetlight_out="true")
    assert reported["issue_type"] == "Streetlight not working"
    assert reported["responsible_department"] == "Electricity (public lighting)"
    assert reported["severity"] == "Medium"
    assert reported["confidence"] >= 0.5


def test_a_streetlight_fault_without_a_light_in_the_photo_has_zero_confidence() -> None:
    report = analyze("pothole-large.jpg", streetlight_out="true")
    lights = issue(report, "streetlight")
    assert lights["count"] == 0
    assert lights["confidence"] == 0.0
    assert "no streetlight was found" in lights["reason"]


@pytest.mark.parametrize(
    ("name", "severity"),
    [
        ("dumping-roadside.jpg", "Medium"),
        ("dumping-mattress.jpg", "Medium"),
        ("dumping-lane.jpg", "Medium"),
        ("dumping-site.jpg", "High"),
    ],
)
def test_detects_illegal_dumping(name: str, severity: str) -> None:
    report = analyze(name)
    dumping = issue(report, "dumping")
    assert dumping["severity"] == severity
    assert dumping["department"] == "Waste Management (Solid Waste)"
    assert dumping["confidence"] >= 0.33
    assert "dumping" in categories(report)
    assert report["issue_type"] == "Illegal dumping"


@pytest.mark.parametrize(
    "name",
    [
        "pothole-single.jpg", "pothole-close.jpg", "pothole-cluster.jpg", "pothole-large.jpg",
        "crack-lengthwise.jpg", "crack-suburb.jpg", "road-clean-desert.jpg",
        "streetlight-durban.jpg", "streetlight-night.jpg",
    ],
)
def test_no_dumping_in_photos_without_any(name: str) -> None:
    assert "dumping" not in categories(analyze(name))


def test_finds_no_road_damage_on_a_clean_road() -> None:
    report = analyze("road-clean-desert.jpg")
    assert not {"pothole", "crack"} & categories(report)
    assert report["issue_type"] == "No issue detected"
    assert report["severity"] == "Low"
    assert report["confidence"] == 0.0


@pytest.mark.parametrize("name", ["pothole-cluster.jpg", "pothole-large.jpg", "crack-suburb.jpg"])
def test_no_streetlight_in_photos_without_one(name: str) -> None:
    assert "streetlight" not in categories(analyze(name))


def test_reports_original_image_size() -> None:
    report = analyze("pothole-close.jpg")
    assert (report["image_width"], report["image_height"]) == (480, 640)


def test_rejects_invalid_image() -> None:
    response = asyncio.run(request(
        "/api/analyze-report",
        files={"image": ("not-image.txt", b"not an image", "text/plain")},
    ))
    assert response.status_code == 400
