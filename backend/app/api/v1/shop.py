"""Cart, wishlist, orders, reviews, coupons, inventory, admin/analytics routers."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ... import models
from ...database import get_db
from ...deps import get_current_user, require_roles
from ...schemas import CartAddIn, CartQtyIn, CheckoutIn, CouponValidateIn, OrderStatusIn, ReviewIn
from ...services import order_service as orders
from ...services import shop_service as shop
from ...services.helpers import product_stock

cart_router = APIRouter()
wishlist_router = APIRouter()
orders_router = APIRouter()
reviews_router = APIRouter()
coupons_router = APIRouter()
inventory_router = APIRouter()
admin_router = APIRouter()
analytics_router = APIRouter()


def _err(code: str, status_code: int = 400):
    return HTTPException(status_code=status_code, detail=code)


# ---- cart ----
@cart_router.get("", summary="Get my cart")
def get_cart(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return shop.serialize_cart(db, shop.get_or_create_cart(db, user.id))


@cart_router.post("/items", summary="Add to cart")
def add_item(data: CartAddIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return shop.add_to_cart(db, user.id, data.product_id, data.variant_id, data.quantity)
    except ValueError as e:
        raise _err(str(e), 404 if "NOT_FOUND" in str(e) else 400)


@cart_router.patch("/items/{item_id}", summary="Update quantity")
def update_qty(item_id: str, data: CartQtyIn, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    try:
        return shop.set_quantity(db, user.id, item_id, data.quantity)
    except ValueError:
        raise _err("ITEM_NOT_FOUND", 404)


@cart_router.delete("/items/{item_id}", summary="Remove item")
def remove_item(item_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return shop.remove_item(db, user.id, item_id)
    except ValueError:
        raise _err("ITEM_NOT_FOUND", 404)


@cart_router.delete("", summary="Clear cart")
def clear(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return shop.clear_cart(db, user.id)


@cart_router.post("/coupon", summary="Apply coupon")
def apply_coupon(data: CouponValidateIn, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    try:
        return shop.apply_coupon(db, user.id, data.code)
    except ValueError:
        raise _err("INVALID_COUPON", 404)


# ---- wishlist ----
@wishlist_router.get("", summary="Get wishlist")
def get_wishlist(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return shop.serialize_wishlist(db, shop.get_or_create_wishlist(db, user.id))


@wishlist_router.post("/{product_id}", summary="Add to wishlist")
def wl_add(product_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not db.get(models.Product, product_id):
        raise _err("PRODUCT_NOT_FOUND", 404)
    return shop.wishlist_add(db, user.id, product_id)


@wishlist_router.delete("/{product_id}", summary="Remove from wishlist")
def wl_remove(product_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return shop.wishlist_remove(db, user.id, product_id)


# ---- orders ----
@orders_router.post("/checkout", summary="Checkout cart -> order")
def checkout(data: CheckoutIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    addr = {}
    if data.address_id:
        a = db.query(models.Address).filter_by(id=data.address_id, user_id=user.id).first()
        if not a:
            raise _err("ADDRESS_NOT_FOUND", 404)
        addr = {"label": a.label, "line1": a.line1, "city": a.city, "state": a.state,
                "postal_code": a.postal_code, "country": a.country}
    elif data.address:
        addr = data.address.model_dump()
    else:
        d = db.query(models.Address).filter_by(user_id=user.id, is_default=True).first()
        addr = {"line1": d.line1 if d else "", "city": d.city if d else ""}
    try:
        return orders.checkout(db, user, addr, data.coupon_code, data.payment_provider)
    except ValueError as e:
        raise _err(str(e))


@orders_router.get("", summary="My orders")
def my_orders(status: str | None = None, page: int = 1, page_size: int = 20,
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    return orders.list_orders(db, user.id, page, page_size, status)


@orders_router.get("/{order_id}", summary="Order detail")
def order_detail(order_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    o = db.query(models.Order).filter(
        ((models.Order.id == order_id) | (models.Order.order_number == order_id))).first()
    if not o:
        raise _err("ORDER_NOT_FOUND", 404)
    if o.user_id != user.id and user.role not in ("admin", "manager"):
        raise _err("FORBIDDEN", 403)
    return orders.serialize_order(db, o)


# ---- reviews ----
@reviews_router.get("/product/{product_id}", summary="Product reviews")
def product_reviews(product_id: str, page: int = 1, page_size: int = 10,
                    db: Session = Depends(get_db)):
    q = db.query(models.Review).filter_by(product_id=product_id).order_by(models.Review.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [orders.serialize_review(db, r) for r in items], "page": page,
            "page_size": page_size, "total": total, "total_pages": max(1, -(-total // page_size))}


@reviews_router.post("/product/{product_id}", summary="Write review", status_code=201)
def write_review(product_id: str, data: ReviewIn, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    if not db.get(models.Product, product_id):
        raise _err("PRODUCT_NOT_FOUND", 404)
    try:
        return orders.add_review(db, user, product_id, data.rating, data.title, data.body)
    except ValueError as e:
        raise _err(str(e), 409)


@reviews_router.post("/{review_id}/helpful", summary="Mark helpful")
def helpful(review_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    r = db.get(models.Review, review_id)
    if not r:
        raise _err("REVIEW_NOT_FOUND", 404)
    r.helpful_count += 1
    db.commit()
    return {"ok": True, "helpful_count": r.helpful_count}


# ---- coupons ----
@coupons_router.get("", summary="Active coupons/offers")
def list_coupons(db: Session = Depends(get_db)):
    cs = db.query(models.Coupon).filter_by(is_active=True).limit(50).all()
    return [{"code": c.code, "description": c.description, "discount_type": c.discount_type,
             "discount_value": float(c.discount_value),
             "min_order_value": float(c.min_order_value or 0)} for c in cs]


@coupons_router.post("/validate", summary="Validate coupon")
def validate(data: CouponValidateIn, db: Session = Depends(get_db)):
    try:
        return orders.validate_coupon(db, data.code, data.subtotal)
    except ValueError as e:
        raise _err(str(e), 404 if "INVALID" in str(e) else 400)


# ---- inventory ----
@inventory_router.get("/product/{product_id}", summary="Stock levels")
def stock(product_id: str, db: Session = Depends(get_db)):
    rows = db.query(models.Inventory).filter_by(product_id=product_id).all()
    return [{"product_id": r.product_id, "variant_id": r.variant_id, "quantity": r.quantity,
             "reserved": r.reserved, "available": max(0, r.quantity - r.reserved)} for r in rows]


@inventory_router.get("/low-stock", summary="Low stock alerts (admin)")
def low_stock(db: Session = Depends(get_db),
              admin=Depends(require_roles("admin", "manager"))):
    rows = db.query(models.Inventory).filter(
        models.Inventory.quantity <= models.Inventory.low_stock_threshold).limit(100).all()
    out = []
    for r in rows:
        p = db.get(models.Product, r.product_id)
        out.append({"product_id": r.product_id, "product_name": p.name if p else "?",
                    "variant_id": r.variant_id, "quantity": r.quantity})
    return out


# ---- admin + analytics ----
@admin_router.get("/overview", summary="Admin overview (live data)")
def overview(db: Session = Depends(get_db),
             admin=Depends(require_roles("admin", "manager"))):
    return orders.analytics_overview(db)


@admin_router.get("/orders", summary="All orders (admin)")
def all_orders(status: str | None = None, page: int = 1, page_size: int = 20,
               db: Session = Depends(get_db),
               admin=Depends(require_roles("admin", "manager"))):
    return orders.list_orders(db, None, page, page_size, status)


@admin_router.patch("/orders/{order_id}", summary="Update order status")
def update_status(order_id: str, data: OrderStatusIn, db: Session = Depends(get_db),
                  admin=Depends(require_roles("admin", "manager"))):
    o = db.get(models.Order, order_id)
    if not o:
        raise _err("ORDER_NOT_FOUND", 404)
    allowed = orders.VALID_TRANSITIONS.get(o.status, set())
    if data.status not in allowed and data.status != o.status:
        raise _err(f"Cannot transition {o.status} -> {data.status}", 422)
    o.status = data.status
    db.commit()
    return orders.serialize_order(db, o)


@analytics_router.get("/overview", summary="Analytics overview")
def analytics(db: Session = Depends(get_db),
              admin=Depends(require_roles("admin", "manager"))):
    return orders.analytics_overview(db)
