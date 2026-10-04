"""Shared helpers: slugs, pagination, serialization, money math."""
import json
import re
import uuid

from sqlalchemy.orm import Session

from .. import models

INR = "INR"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (s or "item")[:120]


def unique_slug(db: Session, model, base: str) -> str:
    slug = slugify(base)
    candidate, n = slug, 2
    while db.query(model).filter_by(slug=candidate).first():
        candidate = f"{slug}-{n}"
        n += 1
    return candidate


def paginate(query, page: int, page_size: int):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = max(1, -(-total // page_size))
    return items, page, page_size, total, total_pages


def product_stock(db: Session, product_id: str) -> int:
    rows = db.query(models.Inventory).filter_by(product_id=product_id).all()
    return sum(max(0, (r.quantity - r.reserved)) for r in rows)


def variant_stock(db: Session, variant_id: str) -> int:
    r = db.query(models.Inventory).filter_by(variant_id=variant_id).first()
    return max(0, (r.quantity - r.reserved)) if r else 0


def serialize_product(db: Session, p: models.Product) -> dict:
    stock = product_stock(db, p.id)
    discount = 0.0
    if p.compare_at_price and float(p.compare_at_price) > 0 and float(p.price) < float(p.compare_at_price):
        discount = round((1 - float(p.price) / float(p.compare_at_price)) * 100, 1)
    imgs = sorted(p.images, key=lambda i: i.position)
    variants = []
    for v in p.variants:
        price = float(v.price_override) if v.price_override is not None else float(p.price)
        variants.append({
            "id": v.id, "sku": v.sku, "name": v.name, "color": v.color, "size": v.size,
            "price_override": float(v.price_override) if v.price_override is not None else None,
            "stock": variant_stock(db, v.id),
        })
    return {
        "id": p.id, "name": p.name, "slug": p.slug, "description": p.description,
        "category": {"id": p.category.id, "name": p.category.name, "slug": p.category.slug,
                      "description": "", "image_url": "", "parent_id": None, "product_count": 0} if p.category else None,
        "brand": {"id": p.brand.id, "name": p.brand.name, "slug": p.brand.slug,
                   "description": "", "logo_url": "", "product_count": 0} if p.brand else None,
        "category_id": p.category_id, "brand_id": p.brand_id,
        "price": float(p.price), "compare_at_price": float(p.compare_at_price or 0),
        "discount_pct": discount, "currency": p.currency,
        "rating_avg": float(p.rating_avg or 0), "rating_count": p.rating_count,
        "sold_count": p.sold_count, "is_featured": p.is_featured, "stock": stock,
        "images": [{"id": i.id, "url": i.url, "alt": i.alt, "position": i.position} for i in imgs],
        "variants": variants,
    }


def cart_totals(db: Session, cart: models.Cart) -> dict:
    from ..models import Coupon
    subtotal = 0.0
    items = []
    for ci in cart.items:
        price = float(ci.product.price)
        if ci.variant and ci.variant.price_override is not None:
            price = float(ci.variant.price_override)
        line = round(price * ci.quantity, 2)
        subtotal += line
        items.append({"ci": ci, "unit": price, "line": line})
    discount = 0.0
    if cart.coupon_code:
        c = db.query(Coupon).filter_by(code=cart.coupon_code.upper(), is_active=True).first()
        if c and subtotal >= float(c.min_order_value or 0):
            if c.discount_type == "percent":
                discount = round(subtotal * float(c.discount_value) / 100, 2)
                if c.max_discount:
                    discount = min(discount, float(c.max_discount))
            else:
                discount = min(float(c.discount_value), subtotal)
    shipping = 0.0 if (subtotal - discount) >= 999 or subtotal == 0 else 49.0
    tax = round(max(0, subtotal - discount) * 0.18, 2)
    total = round(max(0, subtotal - discount) + shipping + tax, 2)
    return {"items": items, "subtotal": round(subtotal, 2), "discount": round(discount, 2),
            "shipping": shipping, "tax": tax, "total": total}


def order_number() -> str:
    return "NC" + uuid.uuid4().hex[:10].upper()


def specs_dict(p: models.Product) -> dict:
    try:
        return json.loads(p.specs or "{}")
    except Exception:
        return {}
