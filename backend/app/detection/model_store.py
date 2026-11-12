"""Download and verify the pothole detection model.

The ONNX file is about 108 MB, so it is not committed. It is fetched from a pinned
Hugging Face revision and checked against the SHA-256 published in that release's
manifest, so a changed or corrupted file is never loaded.

    python -m app.detection.model_store
"""

import hashlib
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

MODEL_ID = "pothole_rfdetr_nano_v4_r1"
MODEL_REPO = "infra-intelligence/pothole-rfdetr-nano"
MODEL_REVISION = "c4f5c3345dce248c8cc6abd655258f670debbdc1"
MODEL_FILE = f"{MODEL_ID}.onnx"
MODEL_SHA256 = "41059ced7b6b58d7308d2d216e18f9ae56d9138f1623f711634d0266c0edbd02"
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}/{MODEL_FILE}"

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "models"


def model_path() -> Path:
    return Path(os.getenv("CIVICLENS_MODEL_PATH", DEFAULT_MODEL_DIR / MODEL_FILE))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_model() -> Path:
    """Return the model path, downloading and verifying the file first if needed."""
    path = model_path()
    if path.is_file() and sha256_of(path) == MODEL_SHA256:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    # Download next to the target and rename, so an interrupted download never
    # leaves a half-written file where the detector looks.
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        with urllib.request.urlopen(MODEL_URL, timeout=120) as response:
            shutil.copyfileobj(response, tmp)
        tmp_path = Path(tmp.name)
    actual = sha256_of(tmp_path)
    if actual != MODEL_SHA256:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Model checksum mismatch: expected {MODEL_SHA256}, got {actual}")
    tmp_path.replace(path)
    return path


if __name__ == "__main__":
    print(ensure_model())
