"""Convert the crack and streetlight models to ONNX.

Both are published only as PyTorch checkpoints. This script downloads each one from
a pinned Hugging Face revision, exports it to ONNX, and refuses to write the file
unless ONNX Runtime gives the same answer as PyTorch on random input. It needs the
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
from app.detection.model_store import CRACK_MODEL, STREETLIGHT_MODEL, model_path  # noqa: E402

# Largest allowed gap between PyTorch and ONNX Runtime outputs on the same input.
TOLERANCE = 1e-2


def check_parity(name: str, onnx_file: Path, run_torch, input_name: str, size: int, opt_level) -> None:
    options = ort.SessionOptions()
    options.graph_optimization_level = opt_level
    session = ort.InferenceSession(str(onnx_file), options, providers=["CPUExecutionProvider"])
    for seed in (0, 1):
        x = torch.rand(1, 3, size, size, generator=torch.Generator().manual_seed(seed))
        with torch.no_grad():
            expected = [t.numpy() for t in run_torch(x)]
        actual = session.run(None, {input_name: x.numpy()})
        gap = max(float(np.abs(a - e).max()) for a, e in zip(actual, expected))
        if gap > TOLERANCE:
            raise SystemExit(f"{name}: ONNX output differs from PyTorch by {gap:.4f}")
    print(f"{name}: ONNX matches PyTorch")


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
        "input",
        spec.input_size,
        ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
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
    # ORT_ENABLE_ALL's layout rewrites change this graph's results, so the app and
    # this check both run it at the extended level.
    check_parity(spec.model_id, target, wrapped, "pixel_values", spec.input_size, ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED)


if __name__ == "__main__":
    torch.manual_seed(0)
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    export_crack_model()
    export_streetlight_model()
