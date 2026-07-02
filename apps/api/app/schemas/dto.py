from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CreateRunRequest(BaseModel):
    target_role: str
    links: list[str] = []


class RunStatus(BaseModel):
    id: int
    target_role: str
    status: str
    error: str = ""


class SuggestionOut(BaseModel):
    id: int
    agent: str
    platform: str
    field: str
    current: str
    suggested: str
    reason: str
    benefit: str
    evidence_ids: list
    status: str
    rejection_reason: str = ""
    artifact_path: str = ""

    model_config = {"from_attributes": True}


class DecisionRequest(BaseModel):
    approve: bool


class ReportOut(BaseModel):
    run_id: int
    scores: dict
    gaps: dict
    roadmap: list
    learning_plan: list

    model_config = {"from_attributes": True}
