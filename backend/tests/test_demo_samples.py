"""The live site's demo samples must be what the models really output.

Runs each sample photo through the backend again and compares it with the saved
result in frontend/public/samples. If a model, a threshold or a rule changes, this
fails until the samples are rebuilt with `python -m tools.make_demo_samples`.
"""

import json
from pathlib import Path

import pytest

from app.main import analyze

BACKEND = Path(__file__).resolve().parents[1]
SAMPLES = BACKEND.parent / "frontend" / "public" / "samples"
INDEX = json.loads((SAMPLES / "index.json").read_text(encoding="utf-8"))
TOLERANCE = 2e-3  # rounding in the saved boxes and scores; ONNX Runtime can differ by a hair between machines


@pytest.fixture(autouse=True)
def no_gemini(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE


@pytest.mark.parametrize("sample", INDEX, ids=[s["id"] for s in INDEX])
def test_saved_sample_matches_the_models(sample: dict) -> None:
    saved = json.loads((SAMPLES / f"{sample['id']}.json").read_text(encoding="utf-8"))
    photo = SAMPLES / f"{sample['id']}.jpg"
    assert photo.read_bytes() == (BACKEND / sample["source"]).read_bytes(), "the shown photo is the one that was analysed"
    fresh = analyze(photo.read_bytes(), "image/jpeg", None, None, sample["streetlightOut"]).model_dump()

    for field in ("issue_type", "severity", "responsible_department", "pothole_count", "image_width", "image_height", "models", "analysis_source"):
        assert fresh[field] == saved[field], field
    assert [(i["category"], i["severity"], i["count"]) for i in fresh["issues"]] == [(i["category"], i["severity"], i["count"]) for i in saved["issues"]]
    assert len(fresh["detections"]) == len(saved["detections"])
    for a, b in zip(sorted(fresh["detections"], key=lambda d: (d["label"], d["x1"])), sorted(saved["detections"], key=lambda d: (d["label"], d["x1"]))):
        assert a["label"] == b["label"]
        assert all(close(a[k], b[k]) for k in ("confidence", "x1", "y1", "x2", "y2")), (a, b)


def test_index_lists_every_saved_sample_with_a_credit() -> None:
    files = {p.stem for p in SAMPLES.glob("*.json")} - {"index"}
    assert files == {s["id"] for s in INDEX}
    assert all(s["credit"] for s in INDEX)
