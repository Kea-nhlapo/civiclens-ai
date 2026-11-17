from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["Low", "Medium", "High", "Critical"]
AnalysisSource = Literal["detector", "detector+gemini"]


class MunicipalReport(BaseModel):
    title: str
    description: str
    location: str
    evidence_notes: str
    priority: Severity
    suggested_department: str


class DetectionBox(BaseModel):
    label: str
    category: Literal["pothole", "crack", "streetlight"]
    confidence: float = Field(ge=0, le=1)
    # Corners as fractions of the image width and height, so the frontend can draw
    # them over the photo at any display size.
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)
    y2: float = Field(ge=0, le=1)


class IssueSummary(BaseModel):
    category: Literal["pothole", "crack", "streetlight"]
    issue_type: str
    department: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    count: int
    coverage: float = Field(ge=0, le=1)
    reason: str


class AnalysisReport(BaseModel):
    issue_type: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    summary: str
    responsible_department: str
    recommended_action: str
    municipal_report: MunicipalReport
    citizen_message: str
    next_steps: list[str]
    detections: list[DetectionBox] = Field(default_factory=list)
    # Every problem found, most severe first. The top-level fields describe issues[0].
    issues: list[IssueSummary] = Field(default_factory=list)
    pothole_count: int = 0
    coverage: float = Field(default=0, ge=0, le=1)
    severity_reason: str = ""
    image_width: int = 0
    image_height: int = 0
    models: list[str] = Field(default_factory=list)
    analysis_source: AnalysisSource = "detector"


class ReportWording(BaseModel):
    """The parts Gemini may rewrite. Facts such as severity stay with the detector."""

    summary: str
    recommended_action: str
    title: str
    description: str
    evidence_notes: str
    citizen_message: str
    next_steps: list[str]
