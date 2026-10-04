"""Pydantic request/response schemas for every endpoint."""
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, EmailStr, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int


# ---------- Auth ----------
class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(default="", max_length=255)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    avatar_url: str = ""
    phone: str = ""
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ProfileUpdateIn(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


class AddressIn(BaseModel):
    label: str = "Home"
    full_name: str = ""
    line1: str = ""
    line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "India"
    phone: str = ""
    is_default: bool = False


class AddressOut(AddressIn):
    id: str
    user_id: str


# ---------- Catalog ----------
class CategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str = ""
    image_url: str = ""
    parent_id: str | None = None
    product_count: int = 0

    class Config:
        from_attributes = True


class BrandOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str = ""
    logo_url: str = ""
    product_count: int = 0

    class Config:
        from_attributes = True


class ProductImageOut(BaseModel):
    id: str
    url: str
    alt: str = ""
    position: int = 0

    class Config:
        from_attributes = True


class VariantOut(BaseModel):
    id: str
    sku: str
    name: str = ""
    color: str = ""
    size: str = ""
    price_override: float | None = None
    stock: int = 0

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str = ""
    category: CategoryOut | None = None
    brand: BrandOut | None = None
    category_id: str | None = None
    brand_id: str | None = None
    price: float
    compare_at_price: float = 0
    discount_pct: float = 0
    currency: str = "INR"
    rating_avg: float = 0
    rating_count: int = 0
    sold_count: int = 0
    is_featured: bool = False
    stock: int = 0
    images: list[ProductImageOut] = []
    variants: list[VariantOut] = []

    class Config:
        from_attributes = True


class ProductCreateIn(BaseModel):
    name: str
    description: str = ""
    category_id: str | None = None
    brand_id: str | None = None
    price: float = Field(ge=0)
    compare_at_price: float = 0
    is_featured: bool = False
    specs: dict[str, Any] = {}
    tags: str = ""


class ProductPatchIn(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    compare_at_price: float | None = None
    is_active: bool | None = None
    is_featured: bool | None = None


# ---------- Cart / wishlist ----------
class CartAddIn(BaseModel):
    product_id: str
    variant_id: str | None = None
    quantity: int = Field(default=1, ge=1, le=99)


class CartQtyIn(BaseModel):
    quantity: int = Field(ge=0, le=99)


class CartItemOut(BaseModel):
    id: str
    product: ProductOut
    variant: VariantOut | None = None
    quantity: int
    unit_price: float
    line_total: float


class CartOut(BaseModel):
    id: str
    items: list[CartItemOut] = []
    subtotal: float = 0
    discount: float = 0
    shipping: float = 0
    tax: float = 0
    total: float = 0
    coupon_code: str = ""


class WishlistOut(BaseModel):
    id: str
    items: list[ProductOut] = []


# ---------- Orders ----------
class CheckoutIn(BaseModel):
    address_id: str | None = None
    address: AddressIn | None = None
    coupon_code: str = ""
    payment_provider: str = "mock"


OrderStatus = Literal["pending", "confirmed", "processing", "shipped", "out_for_delivery",
                       "delivered", "cancelled", "returned", "refunded"]


class OrderItemOut(BaseModel):
    id: str
    product_id: str
    product_name: str
    variant_name: str = ""
    quantity: int
    unit_price: float
    total_price: float


class OrderOut(BaseModel):
    id: str
    order_number: str
    status: str
    subtotal: float
    discount: float
    shipping: float
    tax: float
    total: float
    currency: str = "INR"
    coupon_code: str = ""
    payment_status: str
    created_at: datetime | None = None
    items: list[OrderItemOut] = []
    tracking_number: str = ""


class OrderStatusIn(BaseModel):
    status: str


# ---------- Reviews ----------
class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = ""
    body: str = ""


class ReviewOut(BaseModel):
    id: str
    product_id: str
    user_name: str = ""
    rating: int
    title: str = ""
    body: str = ""
    is_verified_purchase: bool = False
    helpful_count: int = 0
    created_at: datetime | None = None


# ---------- Coupons ----------
class CouponOut(BaseModel):
    code: str
    description: str = ""
    discount_type: str
    discount_value: float
    min_order_value: float = 0

    class Config:
        from_attributes = True


class CouponValidateIn(BaseModel):
    code: str
    subtotal: float = 0


# ---------- Inventory ----------
class InventoryOut(BaseModel):
    product_id: str
    variant_id: str | None = None
    quantity: int
    reserved: int
    available: int


# ---------- Search ----------
class SearchOut(BaseModel):
    items: list[ProductOut]
    page: int
    page_size: int
    total: int
    total_pages: int
    suggestions: list[str] = []


# ---------- Agent ----------
class AgentChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class AgentProductRef(BaseModel):
    id: str
    name: str
    slug: str
    price: float
    rating_avg: float = 0
    image_url: str = ""


class AgentChatOut(BaseModel):
    conversation_id: str
    reply: str
    products: list[AgentProductRef] = []


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime | None = None
