from typing import Literal

from pydantic import BaseModel, Field


class ExplainedTest(BaseModel):
    test: str
    plain_english: str


class FlaggedTest(BaseModel):
    test: str
    severity: Literal["Normal", "Watch", "High priority", "Critical"]
    reason: str


class DoctorQuestion(BaseModel):
    question: str


class LabValue(BaseModel):
    test_name: str
    value: float | None = None
    unit: str = ""
    reference_range: str = ""
    status: Literal["Low", "Normal", "High", "Critical", "Unknown"] = "Unknown"
    page_number: int = 1
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    original_text: str = ""
    reported_flag: str = ""
    verification_needed: bool = False


class AgentOutputs(BaseModel):
    explanations: list[ExplainedTest]
    flags: list[FlaggedTest]
    questions: list[DoctorQuestion]
    disclaimer: str
