"""认证 DTO。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    user_id: str = Field(..., alias="userId")
    password: str

    model_config = {"populate_by_name": True}


class TokenResponse(BaseModel):
    access_token: str = Field(..., alias="accessToken")
    user_id: str = Field(..., alias="userId")
    role: str
    expires_in_seconds: int = Field(..., alias="expiresInSeconds")

    model_config = {"populate_by_name": True}

    @classmethod
    def of(cls, token: str, user_id: str, role: str, expires_in: int) -> "TokenResponse":
        return cls(accessToken=token, userId=user_id, role=role, expiresInSeconds=expires_in)

    @classmethod
    def profile(cls, user_id: str, role: str) -> "TokenResponse":
        return cls(accessToken="", userId=user_id, role=role, expiresInSeconds=0)


class MessageResponse(BaseModel):
    success: bool = True
    message: str
