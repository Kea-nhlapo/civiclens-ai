"""Where the three detection models come from, and how to get them onto disk.

None of the model files are committed; together they are about 625 MB.

- The pothole model is published as ONNX. It is downloaded from a pinned Hugging
  Face revision and checked against the SHA-256 in that release's manifest.
- The crack, streetlight and dumping models are published only as PyTorch checkpoints.
  tools/export_models.py converts them to ONNX from pinned revisions and checks the
  result against PyTorch. The Docker build and CI run it; the app only loads the
  files it produced.

    python -m app.detection.model_store     # pothole model only
    python -m tools.export_models           # crack, streetlight and dumping models
"""

import hashlib
import os
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "models"


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    repo: str
    revision: str
    source_file: str
    input_size: int
    classes: tuple[str, ...]
    threshold: float
    sha256: str | None = None  # only for files downloaded as-is

    @property
    def file_name(self) -> str:
        return f"{self.model_id}.onnx"

    @property
    def url(self) -> str:
        return f"https://huggingface.co/{self.repo}/resolve/{self.revision}/{self.source_file}"


POTHOLE_MODEL = ModelSpec(
    model_id="pothole_rfdetr_nano_v4_r1",
    repo="infra-intelligence/pothole-rfdetr-nano",
    revision="c4f5c3345dce248c8cc6abd655258f670debbdc1",
    source_file="pothole_rfdetr_nano_v4_r1.onnx",
    input_size=384,
    classes=("pothole",),
    # The model's published operating threshold, chosen for precision around 0.8.
    threshold=0.45,
    sha256="41059ced7b6b58d7308d2d216e18f9ae56d9138f1623f711634d0266c0edbd02",
)

CRACK_MODEL = ModelSpec(
    model_id="rdd2022_rfdetr_small",
    repo="dronefreak/rdd2022-rfdetr-small",
    revision="51718250c97c40e7ddf2f586695a441fa19fb38b",
    source_file="checkpoint_best_total.pth",
    input_size=512,
    # The checkpoint's own class order. Its pothole class is ignored: the dedicated
    # pothole model has fewer false alarms.
    classes=("longitudinal_crack", "transverse_crack", "alligator_crack", "pothole"),
    threshold=0.35,
)

STREETLIGHT_MODEL = ModelSpec(
    model_id="dfine_small_obj365",
    repo="ustc-community/dfine-small-obj365",
    revision="2f6da2b7f591abc61a55beda9debd67aca3ef4d3",
    source_file="model.safetensors",
    input_size=640,
    classes=("Street Lights",),
    threshold=0.50,
)

DUMPING_MODEL = ModelSpec(
    model_id="owlv2_base_dumping_672",
    repo="google/owlv2-base-patch16-ensemble",
    revision="cfd3195ba4ea9592eec887ded089f4c08eff231d",
    source_file="model.safetensors",
    # OWLv2 is trained at 960x960, but that takes about 5 s per photo on a laptop
    # CPU. At 672 it takes under 2 s and found the same dumping photos in testing.
    input_size=672,
    # Zero-shot: these text prompts are baked into the exported model.
    classes=(
        "a pile of rubbish",
        "dumped garbage bags",
        "illegal dumping of rubble",
        "a pile of litter on the ground",
        "an old mattress dumped on the street",
    ),
    threshold=0.33,
)

ALL_MODELS = (POTHOLE_MODEL, CRACK_MODEL, STREETLIGHT_MODEL, DUMPING_MODEL)


def model_dir() -> Path:
    return Path(os.getenv("CIVICLENS_MODEL_DIR", DEFAULT_MODEL_DIR))


def model_path(spec: ModelSpec) -> Path:
    return model_dir() / spec.file_name


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_verified(spec: ModelSpec) -> Path:
    """Return the model path, downloading and verifying the file first if needed."""
    path = model_path(spec)
    if path.is_file() and sha256_of(path) == spec.sha256:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    # Download next to the target and rename, so an interrupted download never
    # leaves a half-written file where the detector looks.
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        with urllib.request.urlopen(spec.url, timeout=120) as response:
            shutil.copyfileobj(response, tmp)
        tmp_path = Path(tmp.name)
    actual = sha256_of(tmp_path)
    if actual != spec.sha256:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"{spec.model_id} checksum mismatch: expected {spec.sha256}, got {actual}")
    tmp_path.replace(path)
    return path


def ensure_model(spec: ModelSpec) -> Path:
    if spec.sha256:
        return download_verified(spec)
    path = model_path(spec)
    if not path.is_file():
        raise RuntimeError(f"{spec.model_id} is missing at {path}. Run: python -m tools.export_models")
    return path


if __name__ == "__main__":
    print(download_verified(POTHOLE_MODEL))
