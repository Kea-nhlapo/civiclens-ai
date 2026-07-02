import os
import asyncio

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import AnalysisReport
from app.services.gemini_service import analyze_with_gemini
from app.utils.image_utils import validate_image

app = FastAPI(title="CivicLens AI Backend", version="1.0.0")
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


@app.post("/api/analyze-report", response_model=AnalysisReport)
async def analyze_report(
    image: UploadFile = File(...),
    location: str | None = Form(default=None),
    notes: str | None = Form(default=None),
) -> AnalysisReport:
    data = await image.read()
    try:
        mime_type = validate_image(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await asyncio.to_thread(analyze_with_gemini, data, mime_type, location, notes)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
