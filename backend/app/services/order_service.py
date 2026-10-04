"""Orders, coupons, reviews, inventory, analytics services."""
import json
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .. import models
from .helpers import cart_totals, order_number
from .shop_service import get_or_create_cart

VALID_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"processing", "cancelled"},
    "processing": {"shipped", "cancelled"},
    "shipped": {"out_for_delivery", "returned"},
    "out_for_delivery": {"delivered", "returned"},
    "delivered": {"returned", "refunded"},
    "cancelled": set(), "returned": {"refunded"}, "refunded": set(),
}


def checkout(db: Session, user: models.User, address: dict, coupon_code="", provider="mock"):
    cart = get_or_create_cart(db, user.id)
    if coupon_code:
        cart.coupon_code = coupon_code.upper()
        db.commit()
    t = cart_totals(db, cart)
    if not cart.items:
        raise ValueError("EMPTY_CART")
    order = models.Order(
        order_number=order_number(), user_id=user.id, status="confirmed",
        subtotal=t["subtotal"], discount=t["discount"], shipping=t["shipping"],
        tax=t["tax"], total=t["total"], coupon_code=cart.coupon_code or "",
        shipping_address=json.dumps(address), payment_status="paid" if provider != "cod" else "pending",
    )
    db.add(order)
    db.flush()
    for ci in cart.items:
        price = float(ci.product.price)
        if ci.variant and ci.variant.price_override is not None:
            price = float(ci.variant.price_override)
        db.add(models.OrderItem(order_id=order.id, product_id=ci.product_id,
                                variant_id=ci.variant_id, product_name=ci.product.name,
                                variant_name=ci.variant.name if ci.variant else "",
                                quantity=ci.quantity, unit_price=price,
                                total_price=round(price * ci.quantity, 2)))
        inv = db.query(models.Inventory).filter_by(product_id=ci.product_id,
                                                   variant_id=ci.variant_id).first()
        if inv is None:
            inv = db.query(models.Inventory).filter_by(product_id=ci.product_id, variant_id=None).first()
        if inv:
            inv.quantity = max(0, inv.quantity - ci.quantity)
            db.add(models.InventoryTransaction(product_id=ci.product_id, variant_id=ci.variant_id,
                                               delta=-ci.quantity, reason="order"))
    db.add(models.Payment(order_id=order.id, provider=provider, status="paid" if provider != "cod" else "pending",
                          amount=order.total, transaction_ref="TXN" + order.order_number))
    db.add(models.Shipment(order_id=order.id, tracking_number="TRK" + order.order_number,
                           status="processing",
                           estimated_delivery=datetime.utcnow() + timedelta(days=5)))
    if cart.coupon_code:
        c = db.query(models.Coupon).filter_by(code=cart.coupon_code).first()
        if c:
            c.used_count += 1
            db.add(models.CouponUsage(coupon_id=c.id, user_id=user.id, order_id=order.id))
    for ci in list(cart.items):
        db.delete(ci)
    cart.coupon_code = ""
    db.add(models.Notification(user_id=user.id, title="Order confirmed",
                               body=f"Order {order.order_number} of ₹{float(order.total):,.0f} is confirmed."))
    db.commit()
    db.refresh(order)
    return serialize_order(db, order)


def serialize_order(db: Session, o: models.Order) -> dict:
    ship = db.query(models.Shipment).filter_by(order_id=o.id).first()
    return {"id": o.id, "order_number": o.order_number, "status": o.status,
            "subtotal": float(o.subtotal), "discount": float(o.discount),
            "shipping": float(o.shipping), "tax": float(o.tax), "total": float(o.total),
            "currency": o.currency, "coupon_code": o.coupon_code or "",
            "payment_status": o.payment_status, "created_at": o.created_at,
            "items": [{"id": i.id, "product_id": i.product_id, "product_name": i.product_name,
                       "variant_name": i.variant_name, "quantity": i.quantity,
                       "unit_price": float(i.unit_price), "total_price": float(i.total_price)} for i in o.items],
            "tracking_number": ship.tracking_number if ship else ""}


def list_orders(db: Session, user_id=None, page=1, page_size=20, status=None):
    q = db.query(models.Order).options(joinedload(models.Order.items)).order_by(models.Order.created_at.desc())
    if user_id:
        q = q.filter_by(user_id=user_id)
    if status:
        q = q.filter_by(status=status)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [serialize_order(db, o) for o in items], "page": page,
            "page_size": page_size, "total": total, "total_pages": max(1, -(-total // page_size))}


def purchased_product_ids(db: Session, user_id: str) -> set[str]:
    rows = db.query(models.OrderItem.product_id).join(models.Order).filter(
        models.Order.user_id == user_id,
        models.Order.status.in_(["confirmed", "processing", "shipped", "out_for_delivery", "delivered"])).all()
    return {r[0] for r in rows}


def add_review(db: Session, user: models.User, product_id: str, rating: int, title="", body=""):
    existing = db.query(models.Review).filter_by(product_id=product_id, user_id=user.id).first()
    if existing:
        raise ValueError("ALREADY_REVIEWED")
    verified = product_id in purchased_product_ids(db, user.id)
    r = models.Review(product_id=product_id, user_id=user.id, rating=rating,
                      title=title, body=body, is_verified_purchase=verified)
    db.add(r)
    db.flush()
    avg = db.query(func.avg(models.Review.rating)).filter_by(product_id=product_id).scalar() or 0
    cnt = db.query(models.Review).filter_by(product_id=product_id).count()
    p = db.get(models.Product, product_id)
    if p:
        p.rating_avg = round(float(avg), 2)
        p.rating_count = cnt
    db.commit()
    return serialize_review(db, r)


def serialize_review(db: Session, r: models.Review) -> dict:
    u = db.get(models.User, r.user_id)
    name = (u.full_name or u.email.split("@")[0]) if u else "Customer"
    return {"id": r.id, "product_id": r.product_id, "user_name": name, "rating": r.rating,
            "title": r.title, "body": r.body, "is_verified_purchase": r.is_verified_purchase,
            "helpful_count": r.helpful_count, "created_at": r.created_at}


def validate_coupon(db: Session, code: str, subtotal: float = 0) -> dict:
    c = db.query(models.Coupon).filter_by(code=code.upper(), is_active=True).first()
    if not c:
        raise ValueError("INVALID_COUPON")
    if subtotal < float(c.min_order_value or 0):
        raise ValueError(f"Minimum order ₹{float(c.min_order_value):,.0f} required")
    if c.used_count >= c.usage_limit:
        raise ValueError("COUPON_EXHAUSTED")
    if c.discount_type == "percent":
        d = round(subtotal * float(c.discount_value) / 100, 2)
        if c.max_discount:
            d = min(d, float(c.max_discount))
    else:
        d = min(float(c.discount_value), subtotal)
    return {"code": c.code, "description": c.description, "discount_type": c.discount_type,
            "discount_value": float(c.discount_value), "min_order_value": float(c.min_order_value),
            "discount_amount": d}


def analytics_overview(db: Session) -> dict:
    revenue = db.query(func.coalesce(func.sum(models.Order.total), 0)).filter(
        models.Order.status.notin_(["cancelled", "refunded"])).scalar() or 0
    orders = db.query(models.Order).count()
    customers = db.query(models.User).filter_by(role="customer").count()
    products = db.query(models.Product).filter_by(is_deleted=False).count()
    aov = round(float(revenue) / orders, 2) if orders else 0
    low_stock = db.query(models.Inventory).filter(
        models.Inventory.quantity <= models.Inventory.low_stock_threshold).count()
    # revenue last 14 days
    series = []
    for i in range(13, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        nxt = day + timedelta(days=1)
        s = db.query(func.coalesce(func.sum(models.Order.total), 0)).filter(
            models.Order.created_at >= day, models.Order.created_at < nxt,
            models.Order.status.notin_(["cancelled", "refunded"])).scalar() or 0
        o = db.query(models.Order).filter(models.Order.created_at >= day,
                                          models.Order.created_at < nxt).count()
        series.append({"date": str(day), "revenue": float(s), "orders": o})
    top = db.query(models.OrderItem.product_name,
                   func.sum(models.OrderItem.quantity).label("qty"),
                   func.sum(models.OrderItem.total_price).label("rev")).group_by(
        models.OrderItem.product_name).order_by(func.sum(models.OrderItem.total_price).desc()).limit(8).all()
    cat = db.query(models.Category.name, func.count(models.Product.id)).join(
        models.Product, models.Product.category_id == models.Category.id, isouter=True).group_by(
        models.Category.name).limit(10).all()
    return {"revenue": float(revenue), "orders": orders, "customers": customers,
            "products": products, "avg_order_value": aov, "low_stock_count": low_stock,
            "conversion_rate": round(min(8.5, (orders / max(1, customers)) * 100), 2),
            "refunds": db.query(models.Order).filter_by(status="refunded").count(),
            "revenue_series": series,
            "top_products": [{"name": n, "qty": int(q or 0), "revenue": float(r or 0)} for n, q, r in top],
            "category_split": [{"name": n or "Uncategorized", "count": int(c)} for n, c in cat]}
