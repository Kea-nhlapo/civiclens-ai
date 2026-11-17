"""Find potholes, road cracks and streetlights in a photo with three open models.

Every model runs on ONNX Runtime on the CPU and is loaded the first time it is
needed. Each one has its own input size and output format, so each gets a small
runner that turns its raw output into the same Detection type:

- Potholes: RF-DETR Nano, following its published contract (MODEL_CONTRACT.md in
  the model repo): stretch to 384x384, raw 0-255 RGB in, normalised
  [x1, y1, x2, y2, score, class] rows out.
- Cracks: RF-DETR Small trained on RDD2022, exported by tools/export_models.py.
  rfdetr resizes without antialiasing and normalises with ImageNet mean/std; boxes
  come out as normalised centre/size and scores as logits.
- Streetlights: D-FINE Small trained on Objects365, exported the same way. Input is
  640x640 RGB scaled to 0-1; only the "Street Lights" class is kept.

DETR-style models need no non-maximum suppression, but they can box the same thing
twice, so a box mostly inside a stronger box of the same label is dropped.
"""

import os
import threading
from dataclasses import dataclass
from io import BytesIO

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

from app.detection.model_store import CRACK_MODEL, POTHOLE_MODEL, STREETLIGHT_MODEL, ModelSpec, ensure_model

# Drop a box when this much of it lies inside a higher-scoring box of the same label.
CONTAINED_FRACTION = 0.8
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
CRACK_LABELS = ("longitudinal_crack", "transverse_crack", "alligator_crack")


@dataclass(frozen=True)
class Detection:
    label: str
    category: str
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
    models: tuple[str, ...] = ()

    def of(self, category: str) -> list[Detection]:
        return [d for d in self.detections if d.category == category]


def load_photo(data: bytes) -> Image.Image:
    """Open the upload upright: phone photos often store rotation in EXIF only."""
    with Image.open(BytesIO(data)) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def threshold_for(spec: ModelSpec) -> float:
    override = os.getenv(f"CIVICLENS_THRESHOLD_{spec.model_id.upper()}")
    return float(override) if override else spec.threshold


def resize_bilinear(pixels: np.ndarray, height: int, width: int) -> np.ndarray:
    """Bilinear resize matching torch's interpolate(align_corners=False, antialias=False).

    rfdetr preprocesses this way, and PIL's bilinear filter antialiases when it
    shrinks, which changes the crack model's scores noticeably.
    """
    in_h, in_w = pixels.shape[:2]
    ys = np.clip((np.arange(height) + 0.5) * (in_h / height) - 0.5, 0, in_h - 1)
    xs = np.clip((np.arange(width) + 0.5) * (in_w / width) - 0.5, 0, in_w - 1)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    y1, x1 = np.minimum(y0 + 1, in_h - 1), np.minimum(x0 + 1, in_w - 1)
    wy, wx = (ys - y0)[:, None, None], (xs - x0)[None, :, None]
    top = pixels[y0][:, x0] * (1 - wx) + pixels[y0][:, x1] * wx
    bottom = pixels[y1][:, x0] * (1 - wx) + pixels[y1][:, x1] * wx
    return (top * (1 - wy) + bottom * wy).astype(np.float32)


def _box(label: str, category: str, score: float, x1: float, y1: float, x2: float, y2: float) -> Detection:
    clip = lambda v: round(float(np.clip(v, 0, 1)), 4)  # noqa: E731
    return Detection(label, category, round(float(score), 4), clip(x1), clip(y1), clip(x2), clip(y2))


def _from_centre(label: str, category: str, score: float, cx: float, cy: float, w: float, h: float) -> Detection:
    return _box(label, category, score, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def _overlap(inner: Detection, outer: Detection) -> float:
    width = min(inner.x2, outer.x2) - max(inner.x1, outer.x1)
    height = min(inner.y2, outer.y2) - max(inner.y1, outer.y1)
    if width <= 0 or height <= 0 or inner.area <= 0:
        return 0.0
    return width * height / inner.area


def drop_contained(detections: list[Detection]) -> list[Detection]:
    kept: list[Detection] = []
    for candidate in sorted(detections, key=lambda d: d.confidence, reverse=True):
        same_label = (k for k in kept if k.label == candidate.label)
        if all(_overlap(candidate, existing) < CONTAINED_FRACTION for existing in same_label):
            kept.append(candidate)
    return kept


class _Runner:
    spec: ModelSpec
    opt_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    def __init__(self) -> None:
        self._session: ort.InferenceSession | None = None
        self._lock = threading.Lock()

    def session(self) -> ort.InferenceSession:
        if self._session is None:
            with self._lock:
                if self._session is None:
                    options = ort.SessionOptions()
                    options.graph_optimization_level = self.opt_level
                    self._session = ort.InferenceSession(
                        str(ensure_model(self.spec)), options, providers=["CPUExecutionProvider"]
                    )
        return self._session

    def detect(self, image: Image.Image) -> list[Detection]:
        raise NotImplementedError


class PotholeRunner(_Runner):
    spec = POTHOLE_MODEL

    def detect(self, image: Image.Image) -> list[Detection]:
        size, cutoff = self.spec.input_size, threshold_for(self.spec)
        batch = np.asarray(image.resize((size, size), Image.BILINEAR), dtype=np.float32).transpose(2, 0, 1)[None]
        rows = self.session().run(["dets6"], {"image": batch})[0][0]
        return [_box("pothole", "pothole", s, x1, y1, x2, y2) for x1, y1, x2, y2, s, _ in rows if s >= cutoff]


class CrackRunner(_Runner):
    spec = CRACK_MODEL

    def detect(self, image: Image.Image) -> list[Detection]:
        size, cutoff = self.spec.input_size, threshold_for(self.spec)
        pixels = resize_bilinear(np.asarray(image, dtype=np.float32) / 255, size, size)
        batch = ((pixels - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1)[None].astype(np.float32)
        boxes, logits = self.session().run(["dets", "labels"], {"input": batch})
        scores = _sigmoid(logits[0])  # [queries, classes + 1]
        found = []
        for query, class_id in zip(*np.nonzero(scores >= cutoff)):
            if class_id < len(CRACK_LABELS):
                found.append(_from_centre(CRACK_LABELS[class_id], "crack", scores[query, class_id], *boxes[0][query]))
        return found


class StreetlightRunner(_Runner):
    spec = STREETLIGHT_MODEL
    # ORT_ENABLE_ALL's layout rewrites change this graph's results; see tools/export_models.py.
    opt_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
    class_id = 12  # "Street Lights" in the Objects365 label map

    def detect(self, image: Image.Image) -> list[Detection]:
        size, cutoff = self.spec.input_size, threshold_for(self.spec)
        pixels = np.asarray(image.resize((size, size), Image.BILINEAR), dtype=np.float32) / 255
        logits, boxes = self.session().run(["logits", "pred_boxes"], {"pixel_values": pixels.transpose(2, 0, 1)[None]})
        scores = _sigmoid(logits[0][:, self.class_id])
        return [_from_centre("streetlight", "streetlight", s, *b) for s, b in zip(scores, boxes[0]) if s >= cutoff]


class Detector:
    def __init__(self) -> None:
        self.runners: tuple[_Runner, ...] = (PotholeRunner(), CrackRunner(), StreetlightRunner())

    def warm_up(self) -> None:
        for runner in self.runners:
            runner.session()

    def detect(self, image: Image.Image) -> DetectionResult:
        found: list[Detection] = []
        for runner in self.runners:
            found.extend(runner.detect(image))
        width, height = image.size
        return DetectionResult(
            detections=drop_contained(found),
            image_width=width,
            image_height=height,
            models=tuple(r.spec.model_id for r in self.runners),
        )


detector = Detector()
