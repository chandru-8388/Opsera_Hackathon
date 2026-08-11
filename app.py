import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError
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

SYSTEM_PROMPT = (
    "You are an expert Site Reliability Engineer (SRE) with deep experience "
    "diagnosing production failures across distributed systems, cloud infrastructure, "
    "and application stacks.\n\n"
    "Your task is to analyze the failure log provided by the user and produce a "
    "precise root-cause analysis.\n\n"
    "Reason through the log systematically before forming your conclusion:\n"
    "1. Read the full log carefully and identify every error signal, exception, "
    "warning, and anomaly.\n"
    "2. Trace the chain of events to determine the root cause — the earliest or "
    "most fundamental failure that triggered any downstream cascade.\n"
    "3. Cite specific lines, error messages, codes, class names, or timestamps "
    "from the log as evidence supporting your diagnosis.\n"
    "4. Propose concrete, actionable remediation steps that directly address the "
    "identified root cause — not generic best practices.\n\n"
    "Ground your analysis strictly in the information present in the log. "
    "Do not speculate about causes that are not evidenced by the log content. "
    "If the log lacks sufficient detail to determine a root cause with confidence, "
    "state what additional information (logs, metrics, config) would be required."
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


def analyze_log(log_text: str) -> AnalysisResponse:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": log_text},
        ],
        response_format=AnalysisResponse,
    )
    message = completion.choices[0].message
    if message.refusal is not None:
        raise HTTPException(
            status_code=502,
            detail="The model refused to analyze this log. Please try a different log snippet.",
        )
    if message.parsed is None:
        raise HTTPException(
            status_code=502,
            detail="Failed to parse the model response. Please try again.",
        )
    return message.parsed


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: LogRequest) -> AnalysisResponse:
    try:
        return analyze_log(request.log)
    except HTTPException:
        raise  # refusal / None-parsed 502s from analyze_log pass through unchanged
    except APITimeoutError:
        raise HTTPException(
            status_code=502,
            detail="OpenAI API timeout: the request exceeded the time limit. Please try again.",
        )
    except RateLimitError:
        raise HTTPException(
            status_code=502,
            detail="Rate limit exceeded. Please wait a moment and try again.",
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=502,
            detail="Authentication failed. Please verify your OpenAI API key.",
        )
    except APIError:
        raise HTTPException(
            status_code=502,
            detail="OpenAI service error. Please try again later.",
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="An unexpected error occurred. Please try again.",
        )
