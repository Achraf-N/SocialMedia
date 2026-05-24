from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.shop_model import ShopPublicResponse

OrderStatus = Literal["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]


class OrderItemCreate(BaseModel):
    product_id: str = Field(min_length=1)
    quantity: int = Field(ge=1)


class CustomerInfoCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str = Field(min_length=1, max_length=40)
    city: str = Field(min_length=1, max_length=120)
    delivery_address: str = Field(min_length=1, max_length=300)


class OrderCreate(BaseModel):
    session_id: str = Field(min_length=1)
    items: list[OrderItemCreate] = Field(min_length=1)
    customer_info: CustomerInfoCreate


class PublicOrderCreate(BaseModel):
    """Order format used by the LangGraph chatbot."""
    shop_id: str | None = None
    session_id: str | None = None
    product_id: str | None = Field(default=None, min_length=1)
    quantity: int = Field(default=1, ge=1)
    items: list[OrderItemCreate] | None = None
    customer_info: CustomerInfoCreate | None = None
    customer_name: str | None = Field(default=None, min_length=1, max_length=160)
    customer_phone: str | None = Field(default=None, min_length=1, max_length=40)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, min_length=1, max_length=300)
    payment_method: str | None = Field(default=None, max_length=80)


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemDetailResponse(BaseModel):
    product_id: str
    product_name: str | None = None
    quantity: int
    unit_price: float
    total_price: float


class CustomerInfoResponse(BaseModel):
    name: str
    phone: str
    city: str
    delivery_address: str


class OrderResponse(BaseModel):
    id: str
    session_id: str | None = None
    shop_id: str
    shop_name: str | None = None
    items: list[OrderItemDetailResponse]
    total_price: float
    status: str
    customer_info: CustomerInfoResponse
    created_at: datetime
    updated_at: datetime


class OrderListWithShopResponse(BaseModel):
    shop: ShopPublicResponse
    orders: list[OrderResponse]


class OrderDetailWithShopResponse(BaseModel):
    shop: ShopPublicResponse
    order: OrderResponse
