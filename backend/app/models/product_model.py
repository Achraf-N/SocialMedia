from datetime import datetime

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    price: float = Field(ge=0)
    description: str = Field(min_length=1)
    available: bool = True
    category: str = Field(min_length=1, max_length=100)
    stock: int = Field(ge=0)
    delivery_time: str = Field(min_length=1, max_length=80)
    brand: str = Field(min_length=1, max_length=120)
    variants: list[str] = Field(default_factory=list)
    image: str = Field(min_length=1)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    price: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, min_length=1)
    available: bool | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)
    stock: int | None = Field(default=None, ge=0)
    delivery_time: str | None = Field(default=None, min_length=1, max_length=80)
    brand: str | None = Field(default=None, min_length=1, max_length=120)
    variants: list[str] | None = None
    image: str | None = Field(default=None, min_length=1)


class ProductResponse(BaseModel):
    id: str
    owner_id: str
    shop_id: str
    name: str
    price: float
    description: str
    available: bool
    category: str
    stock: int
    delivery_time: str
    brand: str
    variants: list[str]
    image: str
    created_at: datetime
    updated_at: datetime
