"""Cart + wishlist services (used by REST routers and agent tools)."""
from sqlalchemy.orm import Session

from .. import models
from .helpers import cart_totals, serialize_product


def get_or_create_cart(db: Session, user_id: str) -> models.Cart:
    cart = db.query(models.Cart).filter_by(user_id=user_id).first()
    if not cart:
        cart = models.Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def serialize_cart(db: Session, cart: models.Cart) -> dict:
    db.refresh(cart)
    t = cart_totals(db, cart)
    out_items = []
    for row in t["items"]:
        ci = row["ci"]
        prod = serialize_product(db, ci.product)
        var = None
        if ci.variant:
            var = {"id": ci.variant.id, "sku": ci.variant.sku, "name": ci.variant.name,
                    "color": ci.variant.color, "size": ci.variant.size,
                    "price_override": float(ci.variant.price_override) if ci.variant.price_override is not None else None,
                    "stock": 0}
        out_items.append({"id": ci.id, "product": prod, "variant": var,
                           "quantity": ci.quantity, "unit_price": row["unit"], "line_total": row["line"]})
    return {"id": cart.id, "items": out_items, "subtotal": t["subtotal"],
            "discount": t["discount"], "shipping": t["shipping"], "tax": t["tax"],
            "total": t["total"], "coupon_code": cart.coupon_code or ""}


def add_to_cart(db: Session, user_id: str, product_id: str, variant_id=None, quantity=1):
    product = db.get(models.Product, product_id)
    if not product or not product.is_active or product.is_deleted:
        raise ValueError("PRODUCT_NOT_FOUND")
    cart = get_or_create_cart(db, user_id)
    existing = None
    for ci in cart.items:
        if ci.product_id == product_id and (ci.variant_id or None) == (variant_id or None):
            existing = ci
            break
    if existing:
        existing.quantity = min(99, existing.quantity + quantity)
    else:
        db.add(models.CartItem(cart_id=cart.id, product_id=product_id,
                               variant_id=variant_id, quantity=quantity))
    db.commit()
    log_event(db, user_id, "cart_add", product_id)
    return serialize_cart(db, cart)


def set_quantity(db: Session, user_id: str, item_id: str, quantity: int):
    cart = get_or_create_cart(db, user_id)
    ci = db.query(models.CartItem).filter_by(id=item_id, cart_id=cart.id).first()
    if not ci:
        raise ValueError("ITEM_NOT_FOUND")
    if quantity <= 0:
        db.delete(ci)
    else:
        ci.quantity = quantity
    db.commit()
    return serialize_cart(db, cart)


def remove_item(db: Session, user_id: str, item_id: str):
    return set_quantity(db, user_id, item_id, 0)


def clear_cart(db: Session, user_id: str):
    cart = get_or_create_cart(db, user_id)
    for ci in list(cart.items):
        db.delete(ci)
    cart.coupon_code = ""
    db.commit()
    return serialize_cart(db, cart)


def apply_coupon(db: Session, user_id: str, code: str):
    from ..models import Coupon
    cart = get_or_create_cart(db, user_id)
    c = db.query(Coupon).filter_by(code=code.upper(), is_active=True).first()
    if not c:
        raise ValueError("INVALID_COUPON")
    cart.coupon_code = c.code
    db.commit()
    return serialize_cart(db, cart)


def log_event(db: Session, user_id, event_type: str, product_id=None, meta="{}"):
    try:
        db.add(models.UserEvent(user_id=user_id, event_type=event_type,
                                product_id=product_id, metadata_json=meta))
        db.commit()
    except Exception:
        db.rollback()


# ----- wishlist -----
def get_or_create_wishlist(db: Session, user_id: str) -> models.Wishlist:
    w = db.query(models.Wishlist).filter_by(user_id=user_id).first()
    if not w:
        w = models.Wishlist(user_id=user_id)
        db.add(w)
        db.commit()
        db.refresh(w)
    return w


def serialize_wishlist(db: Session, w: models.Wishlist) -> dict:
    return {"id": w.id, "items": [serialize_product(db, i.product) for i in w.items]}


def wishlist_add(db: Session, user_id: str, product_id: str):
    w = get_or_create_wishlist(db, user_id)
    if not any(i.product_id == product_id for i in w.items):
        db.add(models.WishlistItem(wishlist_id=w.id, product_id=product_id))
        db.commit()
        db.refresh(w)
    return serialize_wishlist(db, w)


def wishlist_remove(db: Session, user_id: str, product_id: str):
    w = get_or_create_wishlist(db, user_id)
    for i in list(w.items):
        if i.product_id == product_id:
            db.delete(i)
    db.commit()
    db.refresh(w)
    return serialize_wishlist(db, w)
