from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

app = FastAPI(
    title="Log Analyzer",
    description="AI-powered root-cause analysis for failure logs. "
    "Submit a log snippet to the POST /analyze endpoint and receive "
    "a structured root cause, supporting evidence, and remediation steps.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LogRequest(BaseModel):
    log: str

    @field_validator("log", mode="before")
    @classmethod
    def log_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Log snippet must not be empty")
        return value  # preserve original value; strip is for validation only


class AnalysisResponse(BaseModel):
    root_cause: str
    evidence: list[str]
    remediation_steps: list[str]
