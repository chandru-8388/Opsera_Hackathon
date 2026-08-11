import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
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

# Fail fast at startup if the API key is not configured — never hardcode it.
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


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


def analyze_log(log_text: str) -> AnalysisResponse:
    """Stub implementation — replaced by real OpenAI call in WO-010."""
    return AnalysisResponse(
        root_cause="Stub: NullPointerException in Service.process() at Service.java:42",
        evidence=[
            "Stack trace originates at Service.java line 42",
            "No null guard before method invocation on the injected dependency",
        ],
        remediation_steps=[
            "Add a null check before calling process()",
            "Verify dependency injection configuration in Main.java",
        ],
    )


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: LogRequest) -> AnalysisResponse:
    return analyze_log(request.log)
