from typing import Literal

from pydantic import BaseModel, Field


class MFASetupRequired(BaseModel):
    status: Literal["mfa_setup_required"] = "mfa_setup_required"
    challenge_token: str
    provisioning_uri: str = Field(description="Use this otpauth URI to add the account to an authenticator app.")


class MFARequired(BaseModel):
    status: Literal["mfa_required"] = "mfa_required"
    challenge_token: str


class VerifyMFARequest(BaseModel):
    challenge_token: str = Field(description="Challenge token returned when starting this flow.")
    otp: str = Field(description="Current six-digit authenticator code, including leading zeros.", examples=["012345"])


class MFAConfigured(BaseModel):
    status: Literal["mfa_configured"] = "mfa_configured"


class AccessToken(BaseModel):
    access_token: str = Field(description="JWT to send in the Authorization header as a Bearer token.")
    token_type: Literal["bearer"] = "bearer"


class AuthError(BaseModel):
    detail: str
