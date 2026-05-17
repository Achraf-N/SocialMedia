from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OwnerRegister(BaseModel):
    email: str
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Invalid email address")
        return normalized


class OwnerLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class OwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: datetime
    updated_at: datetime


class AuthResponse(BaseModel):
    owner: OwnerResponse
    token_type: str = "bearer"
