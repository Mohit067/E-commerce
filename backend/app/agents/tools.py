"""Agent tools — every tool calls the service layer, never raw SQL from the model.
Each tool signature: (db, user, **args) -> dict. The runner exposes only these.
"""
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models
from ..services import order_service as orders
from ..services import product_service as products
from ..services import shop_service as shop
from ..services.helpers import product_stock, serialize_product


def _prod_ref(db: Session, p: dict) -> dict:
    img = p["images"][0]["url"] if p.get("images") else ""
    return {"id": p["id"], "name": p["name"], "slug": p["slug"], "price": p["price"],
            "rating_avg": p.get("rating_avg", 0), "image_url": img}


def search_products(db: Session, user, query: str = "", category: str = "",
                    brand: str = "", min_price: float | None = None,
                    max_price: float | None = None, rating: float | None = None,
                    sort: str = "popular", limit: int = 8) -> dict:
    res = products.list_products(db, 1, limit, query, category, brand,
                                 min_price, max_price, rating, sort)
    return {"products": [_prod_ref(db, p) for p in res["items"]], "total": res["total"]}


def get_product(db: Session, user, product_id: str) -> dict:
    p = products.get_product(db, product_id)
    if not p:
        return {"error": "PRODUCT_NOT_FOUND"}
    return {"product": p, "stock": p["stock"]}


def get_products_by_category(db: Session, user, category: str, limit: int = 8) -> dict:
    return search_products(db, user, category=category, limit=limit)


def get_products_by_brand(db: Session, user, brand: str, limit: int = 8) -> dict:
    return search_products(db, user, brand=brand, limit=limit)


def filter_products(db: Session, user, **kwargs) -> dict:
    return search_products(db, user, **kwargs)


def compare_products(db: Session, user, product_ids: list[str]) -> dict:
    out = []
    for pid in product_ids[:4]:
        p = products.get_product(db, pid)
        if p:
            out.append({"id": p["id"], "name": p["name"], "price": p["price"],
                        "compare_at_price": p.get("compare_at_price", 0),
                        "rating_avg": p.get("rating_avg", 0),
                        "rating_count": p.get("rating_count", 0),
                        "stock": p["stock"],
                        "brand": (p.get("brand") or {}).get("name", ""),
                        "category": (p.get("category") or {}).get("name", "")})
    return {"comparison": out}


def get_product_reviews(db: Session, user, product_id: str, limit: int = 5) -> dict:
    q = db.query(models.Review).filter_by(product_id=product_id).order_by(
        desc(models.Review.helpful_count)).limit(limit).all()
    return {"reviews": [orders.serialize_review(db, r) for r in q]}


def get_product_inventory(db: Session, user, product_id: str) -> dict:
    rows = db.query(models.Inventory).filter_by(product_id=product_id).all()
    return {"stock": [{"variant_id": r.variant_id, "quantity": r.quantity,
                       "available": max(0, r.quantity - r.reserved)} for r in rows],
            "total_available": sum(max(0, r.quantity - r.reserved) for r in rows)}


def get_related_products(db: Session, user, product_id: str, limit: int = 6) -> dict:
    rel = products.related_products(db, product_id, limit)
    return {"products": [_prod_ref(db, p) for p in rel]}


def get_recommendations(db: Session, user, limit: int = 8) -> dict:
    # recently viewed categories -> recommend top-rated in those, else global top
    cats: list[str] = []
    if user:
        evs = db.query(models.UserEvent).filter_by(user_id=user.id, event_type="view").order_by(
            desc(models.UserEvent.created_at)).limit(10).all()
        for e in evs:
            if e.product_id:
                p = db.get(models.Product, e.product_id)
                if p and p.category_id and p.category_id not in cats:
                    cats.append(p.category_id)
    out = []
    for cid in cats[:2]:
        res = products.list_products(db, 1, 4, sort="rating")
        out += [p for p in res["items"] if p.get("category_id") == cid]
    if len(out) < limit:
        res = products.list_products(db, 1, limit, sort="rating")
        seen = {p["id"] for p in out}
        out += [p for p in res["items"] if p["id"] not in seen]
    return {"products": [_prod_ref(db, p) for p in out[:limit]]}


def get_current_offers(db: Session, user, limit: int = 10) -> dict:
    cs = db.query(models.Coupon).filter_by(is_active=True).limit(limit).all()
    allp = products.list_products(db, 1, 50, sort="popular")["items"]
    deals = [p for p in allp if p["discount_pct"] > 0][:8]
    return {"coupons": [{"code": c.code, "description": c.description,
                         "discount_type": c.discount_type,
                         "discount_value": float(c.discount_value)} for c in cs],
            "deals": [_prod_ref(db, p) for p in deals]}


def get_user_profile(db: Session, user) -> dict:
    if not user:
        return {"error": "NOT_AUTHENTICATED"}
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}


def get_user_orders(db: Session, user, limit: int = 5) -> dict:
    if not user:
        return {"error": "NOT_AUTHENTICATED"}
    res = orders.list_orders(db, user.id, 1, limit)
    return {"orders": res["items"], "total": res["total"]}


def get_order(db: Session, user, order_id: str) -> dict:
    if not user:
        return {"error": "NOT_AUTHENTICATED"}
    o = db.query(models.Order).filter(
        (models.Order.id == order_id) | (models.Order.order_number == order_id)).first()
    if not o or (o.user_id != user.id and user.role not in ("admin", "manager")):
        return {"error": "ORDER_NOT_FOUND"}
    return {"order": orders.serialize_order(db, o)}


def get_order_status(db: Session, user, order_id: str) -> dict:
    r = get_order(db, user, order_id)
    if "error" in r:
        return r
    o = r["order"]
    return {"order_number": o["order_number"], "status": o["status"],
            "payment_status": o["payment_status"], "tracking_number": o.get("tracking_number", ""),
            "total": o["total"]}


def get_user_cart(db: Session, user) -> dict:
    if not user:
        return {"error": "NOT_AUTHENTICATED"}
    return shop.serialize_cart(db, shop.get_or_create_cart(db, user.id))


def add_to_cart(db: Session, user, product_id: str, variant_id: str | None = None,
                quantity: int = 1) -> dict:
    if not user:
        return {"error": "NOT_AUTHENTICATED — please log in to modify the cart"}
    try:
        return shop.add_to_cart(db, user.id, product_id, variant_id, quantity)
    except ValueError as e:
        return {"error": str(e)}


def remove_from_cart(db: Session, user, item_id: str) -> dict:
    if not user:
        return {"error": "NOT_AUTHENTICATED"}
    try:
        return shop.remove_item(db, user.id, item_id)
    except ValueError as e:
        return {"error": str(e)}


def update_cart_quantity(db: Session, user, item_id: str, quantity: int) -> dict:
    if not user:
        return {"error": "NOT_AUTHENTICATED"}
    try:
        return shop.set_quantity(db, user.id, item_id, quantity)
    except ValueError as e:
        return {"error": str(e)}


def get_user_wishlist(db: Session, user) -> dict:
    if not user:
        return {"error": "NOT_AUTHENTICATED"}
    w = shop.serialize_wishlist(db, shop.get_or_create_wishlist(db, user.id))
    return {"products": [{"id": p["id"], "name": p["name"], "slug": p["slug"],
                          "price": p["price"], "rating_avg": p.get("rating_avg", 0),
                          "image_url": p["images"][0]["url"] if p.get("images") else ""}
                         for p in w["items"]]}


def get_categories(db: Session, user, limit: int = 30) -> dict:
    cats = db.query(models.Category).filter_by(is_active=True).limit(limit).all()
    return {"categories": [{"id": c.id, "name": c.name, "slug": c.slug} for c in cats]}


def get_brands(db: Session, user, limit: int = 60) -> dict:
    bs = db.query(models.Brand).filter_by(is_active=True).limit(limit).all()
    return {"brands": [{"id": b.id, "name": b.name, "slug": b.slug} for b in bs]}


def calculate_cart_total(db: Session, user) -> dict:
    c = get_user_cart(db, user)
    if "error" in c:
        return c
    return {k: c[k] for k in ("subtotal", "discount", "shipping", "tax", "total")}


def validate_coupon(db: Session, user, code: str) -> dict:
    cart = get_user_cart(db, user)
    subtotal = cart.get("subtotal", 0) if "error" not in cart else 0
    try:
        return orders.validate_coupon(db, code, subtotal)
    except ValueError as e:
        return {"error": str(e)}


def get_recently_viewed(db: Session, user, limit: int = 8) -> dict:
    if not user:
        return {"products": []}
    evs = db.query(models.UserEvent).filter_by(user_id=user.id, event_type="view").order_by(
        desc(models.UserEvent.created_at)).limit(limit * 2).all()
    seen, out = set(), []
    for e in evs:
        if e.product_id and e.product_id not in seen:
            p = products.get_product(db, e.product_id)
            if p:
                out.append(_prod_ref(db, p))
                seen.add(e.product_id)
        if len(out) >= limit:
            break
    return {"products": out}


TOOL_REGISTRY = {
    "search_products": search_products, "get_product": get_product,
    "get_products_by_category": get_products_by_category,
    "get_products_by_brand": get_products_by_brand, "filter_products": filter_products,
    "compare_products": compare_products, "get_product_reviews": get_product_reviews,
    "get_product_inventory": get_product_inventory,
    "get_related_products": get_related_products,
    "get_recommendations": get_recommendations, "get_current_offers": get_current_offers,
    "get_user_profile": get_user_profile, "get_user_orders": get_user_orders,
    "get_order": get_order, "get_order_status": get_order_status,
    "get_user_cart": get_user_cart, "add_to_cart": add_to_cart,
    "remove_from_cart": remove_from_cart, "update_cart_quantity": update_cart_quantity,
    "get_user_wishlist": get_user_wishlist, "get_categories": get_categories,
    "get_brands": get_brands, "calculate_cart_total": calculate_cart_total,
    "validate_coupon": validate_coupon, "get_user_activity": get_recently_viewed,
    "get_recently_viewed": get_recently_viewed,
}
