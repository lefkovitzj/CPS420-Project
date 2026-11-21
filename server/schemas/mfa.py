from typing import Literal

from pydantic import BaseModel


class MFASetupRequired(BaseModel):
    status: Literal["mfa_setup_required"] = "mfa_setup_required"
    challenge_token: str
    provisioning_uri: str


class MFARequired(BaseModel):
    status: Literal["mfa_required"] = "mfa_required"
    challenge_token: str


class VerifyMFARequest(BaseModel):
    challenge_token: str
    otp: str


class MFAConfigured(BaseModel):
    status: Literal["mfa_configured"] = "mfa_configured"


class AccessToken(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
