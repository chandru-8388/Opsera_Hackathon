from pydantic import BaseModel, field_validator


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
