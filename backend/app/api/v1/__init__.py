from fastapi import APIRouter

from .agent import router as agent_router
from .auth import router as auth_router, users_router
from .catalog import brands_router, categories_router, products_router, search_router
from .shop import (admin_router, analytics_router, cart_router, coupons_router,
                   inventory_router, orders_router, reviews_router, wishlist_router)

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(categories_router, prefix="/categories", tags=["categories"])
api_router.include_router(brands_router, prefix="/brands", tags=["brands"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(cart_router, prefix="/cart", tags=["cart"])
api_router.include_router(wishlist_router, prefix="/wishlist", tags=["wishlist"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(reviews_router, prefix="/reviews", tags=["reviews"])
api_router.include_router(coupons_router, prefix="/coupons", tags=["coupons"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(agent_router, prefix="/agent", tags=["agent"])
