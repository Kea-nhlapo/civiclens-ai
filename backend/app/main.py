import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.detection.detector import detector, load_photo
from app.detection.issues import find_issues
from app.models.schemas import AnalysisReport
from app.services.report_service import build_report
from app.utils.image_utils import validate_image

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Load the model at startup so the first upload does not wait for it. A failure
    # here is logged rather than fatal; the first request retries and reports it.
    try:
        await asyncio.to_thread(detector.warm_up)
    except Exception as exc:
        logger.error("Detection models could not be loaded at startup: %s", exc)
    yield


app = FastAPI(title="CivicLens AI Backend", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "CivicLens AI Backend is running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "CivicLens AI Backend"}


def analyze(
    data: bytes, mime_type: str, location: str | None, notes: str | None, streetlight_out: bool = False
) -> AnalysisReport:
    result = detector.detect(load_photo(data))
    return build_report(result, find_issues(result.detections, streetlight_out), location, notes)


@app.post("/api/analyze-report", response_model=AnalysisReport)
async def analyze_report(
    image: UploadFile = File(...),
    location: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    # A photo can't show whether a light works, so the citizen tells us.
    streetlight_out: bool = Form(default=False),
) -> AnalysisReport:
    data = await image.read()
    try:
        mime_type = validate_image(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        return await asyncio.to_thread(analyze, data, mime_type, location, notes, streetlight_out)
    except (OSError, RuntimeError) as exc:
        logger.error("Detection failed: %s", exc)
        raise HTTPException(status_code=503, detail="The detectors are not available right now. Please try again shortly.") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
