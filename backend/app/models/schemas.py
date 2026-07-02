from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["Low", "Medium", "High", "Critical"]


class MunicipalReport(BaseModel):
    title: str
    description: str
    location: str
    evidence_notes: str
    priority: Severity
    suggested_department: str


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

