"""Convert the crack, streetlight and dumping models to ONNX.

All three are published only as PyTorch checkpoints. This script downloads each one from
a pinned Hugging Face revision, exports it to ONNX, and refuses to keep the file
unless ONNX Runtime finds the same things as PyTorch in a real photo. It needs the
heavy packages in requirements-export.txt, so it runs in a separate Docker build
stage and in CI, never in the running app.

    pip install -r requirements-export.txt
    python -m tools.export_models
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.detection.detector import CrackRunner, DumpingRunner, StreetlightRunner, load_photo  # noqa: E402
from app.detection.model_store import CRACK_MODEL, DUMPING_MODEL, STREETLIGHT_MODEL, model_path  # noqa: E402

PARITY_PHOTOS = Path(__file__).parent / "parity"
# A detection counts if either side scores it at least this high, and the other side
# must find a box in the same place (IoU) with a score within SCORE_GAP.
CONFIDENT = 0.3
MIN_IOU = 0.9
SCORE_GAP = 0.05


def _xyxy(boxes: np.ndarray) -> np.ndarray:
    cx, cy, w, h = boxes.T
    return np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)


def _iou(box: np.ndarray, others: np.ndarray) -> np.ndarray:
    width = np.clip(np.minimum(box[2], others[:, 2]) - np.maximum(box[0], others[:, 0]), 0, None)
    height = np.clip(np.minimum(box[3], others[:, 3]) - np.maximum(box[1], others[:, 1]), 0, None)
    overlap = width * height
    area = lambda b: (b[..., 2] - b[..., 0]) * (b[..., 3] - b[..., 1])  # noqa: E731
    return overlap / (area(box) + area(others) - overlap + 1e-9)


def _unmatched(source, target) -> int:
    (s_scores, s_boxes), (t_scores, t_boxes) = source, target
    missing = 0
    for score, box in zip(s_scores, s_boxes):
        if score < CONFIDENT:
            continue
        same_place = _iou(box, t_boxes) >= MIN_IOU
        if not np.any(same_place & (np.abs(t_scores - score) <= SCORE_GAP)):
            missing += 1
    return missing


def check_parity(name: str, onnx_file: Path, run_torch, runner, photo: str, boxes_first: bool) -> None:
    """Compare detections, not raw output rows.

    These models pick their top candidates with a top-k step, so the same
    detection can come back in a different row, and on random noise near-ties make
    row-by-row comparisons fail for no real reason. A real photo plus matching boxes
    by position tests what matters: the same things found, with the same scores."""
    options = ort.SessionOptions()
    options.graph_optimization_level = runner.opt_level
    session = ort.InferenceSession(str(onnx_file), options, providers=["CPUExecutionProvider"])
    batch = runner.prepare(load_photo((PARITY_PHOTOS / photo).read_bytes()))
    with torch.no_grad():
        expected = [t.numpy() for t in run_torch(torch.from_numpy(batch))]
    actual = session.run(None, {session.get_inputs()[0].name: batch})

    def detections(outputs):
        boxes, logits = outputs if boxes_first else outputs[::-1]
        scores = 1 / (1 + np.exp(-logits[0]))
        return scores.max(axis=1), _xyxy(boxes[0])

    torch_side, onnx_side = detections(expected), detections(actual)
    confident = int((torch_side[0] >= CONFIDENT).sum())
    missing = _unmatched(torch_side, onnx_side) + _unmatched(onnx_side, torch_side)
    if confident == 0:
        raise SystemExit(f"{name}: PyTorch found nothing in {photo}, so the check would prove nothing")
    if missing:
        raise SystemExit(f"{name}: {missing} detection(s) in {photo} differ between ONNX and PyTorch")
    print(f"{name}: ONNX matches PyTorch on {photo} ({confident} detections)")


def export_crack_model() -> None:
    import rfdetr

    spec = CRACK_MODEL
    weights = hf_hub_download(spec.repo, spec.source_file, revision=spec.revision)
    model = rfdetr.RFDETRSmall(pretrain_weights=weights, num_classes=len(spec.classes))
    with tempfile.TemporaryDirectory() as out:
        exported = model.export(output_dir=out, verbose=False)
        target = model_path(spec)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(exported, target)
    inner = model.model.model.eval()
    check_parity(
        spec.model_id,
        target,
        lambda x: (lambda o: (o["pred_boxes"], o["pred_logits"]))(inner(x)),
        CrackRunner(),
        "cracked-road.jpg",
        boxes_first=True,
    )


def export_streetlight_model() -> None:
    from transformers import DFineForObjectDetection

    spec = STREETLIGHT_MODEL
    model = DFineForObjectDetection.from_pretrained(spec.repo, revision=spec.revision).eval()

    class Outputs(torch.nn.Module):
        def __init__(self, inner):
            super().__init__()
            self.inner = inner

        def forward(self, pixel_values):
            out = self.inner(pixel_values=pixel_values)
            return out.logits, out.pred_boxes

    wrapped = Outputs(model).eval()
    target = model_path(spec)
    target.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapped,
        (torch.rand(1, 3, spec.input_size, spec.input_size),),
        str(target),
        input_names=["pixel_values"],
        output_names=["logits", "pred_boxes"],
        opset_version=17,
        dynamo=False,
    )
    check_parity(spec.model_id, target, wrapped, StreetlightRunner(), "streetlights.jpg", boxes_first=False)


def export_dumping_model() -> None:
    """OWLv2 finds objects that match text prompts. The prompts never change, so
    their embeddings are computed once here and stored in the graph as constants.
    That keeps the text encoder out of the file and out of every request."""
    from transformers import Owlv2ForObjectDetection, Owlv2Processor

    spec = DUMPING_MODEL
    model = Owlv2ForObjectDetection.from_pretrained(spec.repo, revision=spec.revision).eval()
    tokenizer = Owlv2Processor.from_pretrained(spec.repo, revision=spec.revision).tokenizer
    tokens = tokenizer(list(spec.classes), padding="max_length", max_length=16, return_tensors="pt")
    with torch.no_grad():
        text = model.owlv2.get_text_features(input_ids=tokens["input_ids"], attention_mask=tokens["attention_mask"])
    text = text if torch.is_tensor(text) else text.pooler_output

    class ImageOnly(torch.nn.Module):
        def __init__(self, inner, queries):
            super().__init__()
            self.inner = inner
            self.register_buffer("queries", queries[None])
            self.register_buffer("query_mask", torch.ones(1, queries.shape[0], dtype=torch.bool))

        def forward(self, pixel_values):
            # interpolate_pos_encoding lets the model run below its native 960x960.
            grid = self.inner.image_embedder(pixel_values=pixel_values, interpolate_pos_encoding=True)[0]
            batch, rows, cols, width = grid.shape
            feats = grid.reshape(batch, rows * cols, width)
            logits, _ = self.inner.class_predictor(feats, self.queries, self.query_mask)
            boxes = self.inner.box_predictor(feats, grid, interpolate_pos_encoding=True)
            return logits, boxes

    wrapped = ImageOnly(model, text).eval()
    target = model_path(spec)
    target.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapped,
        (torch.rand(1, 3, spec.input_size, spec.input_size),),
        str(target),
        input_names=["pixel_values"],
        output_names=["logits", "pred_boxes"],
        opset_version=17,
        dynamo=False,
    )
    check_parity(spec.model_id, target, wrapped, DumpingRunner(), "dumping.jpg", boxes_first=False)


if __name__ == "__main__":
    torch.manual_seed(0)
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    export_crack_model()
    export_streetlight_model()
    export_dumping_model()
