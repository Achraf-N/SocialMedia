from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field

from app.models.shop_model import ShopPublicResponse


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=160)
    delivery_address: str = Field(min_length=1, max_length=300)
    phone_number: str = Field(min_length=1, max_length=40)
    quantity: int = Field(
        ge=1,
        validation_alias=AliasChoices("quantity", "qunatity"),
    )
    product_id: str = Field(min_length=1)
    delivered: bool = False


class OrderUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=1, max_length=160)
    delivery_address: str | None = Field(default=None, min_length=1, max_length=300)
    phone_number: str | None = Field(default=None, min_length=1, max_length=40)
    quantity: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("quantity", "qunatity"),
    )
    product_id: str | None = Field(default=None, min_length=1)
    delivered: bool | None = None


class OrderResponse(BaseModel):
    id: str
    customer_name: str
    delivery_address: str
    phone_number: str
    quantity: int
    product_id: str
    delivered: bool
    created_at: datetime
    updated_at: datetime


class OrderListWithShopResponse(BaseModel):
    shop: ShopPublicResponse
    orders: list[OrderResponse]


class OrderDetailWithShopResponse(BaseModel):
    shop: ShopPublicResponse
    order: OrderResponse
