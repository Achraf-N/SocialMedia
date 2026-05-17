from datetime import datetime

from pydantic import BaseModel, Field


class ShopCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    delivery: str = Field(min_length=1, max_length=80)


class ShopUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    delivery: str | None = Field(default=None, min_length=1, max_length=80)


class ShopResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    delivery: str
    created_at: datetime
    updated_at: datetime


class ShopPublicResponse(BaseModel):
    id: str
    name: str
    delivery: str
    payment: str | None = None
    created_at: datetime
    updated_at: datetime
