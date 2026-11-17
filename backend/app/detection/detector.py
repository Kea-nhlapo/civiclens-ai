"""Pothole detection with RF-DETR Nano running on ONNX Runtime (CPU).

Input and output follow the model's published contract (MODEL_CONTRACT.md in the
model repo): the photo is stretched to a 384x384 RGB square with raw 0-255 values,
and the model returns 300 rows of [x1, y1, x2, y2, score, class_id] with
coordinates normalised to 0-1. Normalisation and the sigmoid happen inside the
graph, and as a DETR-style model it needs no non-maximum suppression.
"""

import os
import threading
from dataclasses import dataclass
from io import BytesIO

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

from app.detection.model_store import MODEL_ID, ensure_model

INPUT_SIZE = 384
# The model's published operating threshold, chosen for precision around 0.8.
DEFAULT_THRESHOLD = 0.45
# DETR can occasionally return a second, smaller box inside one it already found.
# Drop a box when this much of it lies inside a higher-scoring one.
CONTAINED_FRACTION = 0.8


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)


@dataclass(frozen=True)
class DetectionResult:
    detections: list[Detection]
    image_width: int
    image_height: int
    model: str = MODEL_ID


def threshold() -> float:
    return float(os.getenv("CIVICLENS_DETECTION_THRESHOLD", DEFAULT_THRESHOLD))


def load_photo(data: bytes) -> Image.Image:
    """Open the upload upright: phone photos often store rotation in EXIF only."""
    with Image.open(BytesIO(data)) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def _overlap(inner: Detection, outer: Detection) -> float:
    width = min(inner.x2, outer.x2) - max(inner.x1, outer.x1)
    height = min(inner.y2, outer.y2) - max(inner.y1, outer.y1)
    if width <= 0 or height <= 0 or inner.area <= 0:
        return 0.0
    return width * height / inner.area


def drop_contained(detections: list[Detection]) -> list[Detection]:
    kept: list[Detection] = []
    for candidate in sorted(detections, key=lambda d: d.confidence, reverse=True):
        if all(_overlap(candidate, existing) < CONTAINED_FRACTION for existing in kept):
            kept.append(candidate)
    return kept


class PotholeDetector:
    def __init__(self) -> None:
        self._session: ort.InferenceSession | None = None
        self._lock = threading.Lock()

    def _get_session(self) -> ort.InferenceSession:
        if self._session is None:
            with self._lock:
                if self._session is None:
                    self._session = ort.InferenceSession(str(ensure_model()), providers=["CPUExecutionProvider"])
        return self._session

    def warm_up(self) -> None:
        self._get_session()

    def detect(self, image: Image.Image, min_confidence: float | None = None) -> DetectionResult:
        cutoff = threshold() if min_confidence is None else min_confidence
        width, height = image.size
        pixels = np.asarray(image.resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR), dtype=np.float32)
        batch = pixels.transpose(2, 0, 1)[None]
        rows = self._get_session().run(["dets6"], {"image": batch})[0][0]
        found = [
            Detection(
                label="pothole",
                confidence=round(float(score), 4),
                x1=round(float(np.clip(x1, 0, 1)), 4),
                y1=round(float(np.clip(y1, 0, 1)), 4),
                x2=round(float(np.clip(x2, 0, 1)), 4),
                y2=round(float(np.clip(y2, 0, 1)), 4),
            )
            for x1, y1, x2, y2, score, _class_id in rows
            if score >= cutoff
        ]
        return DetectionResult(detections=drop_contained(found), image_width=width, image_height=height)


detector = PotholeDetector()
