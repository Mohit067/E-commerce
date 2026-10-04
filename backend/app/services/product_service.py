"""Product/catalog/search service — single source of truth for agent tools too."""
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .. import models
from .helpers import paginate, serialize_product, unique_slug, slugify


def list_products(db: Session, page=1, page_size=24, search="", category="", brand="",
                  min_price=None, max_price=None, rating=None, sort="popular",
                  in_stock=None, featured=None):
    q = db.query(models.Product).options(joinedload(models.Product.images),
                                         joinedload(models.Product.variants),
                                         joinedload(models.Product.category),
                                         joinedload(models.Product.brand)).filter(
        models.Product.is_active.is_(True), models.Product.is_deleted.is_(False))
    if search:
        like = f"%{search}%"
        q = q.filter(or_(models.Product.name.ilike(like),
                         models.Product.description.ilike(like),
                         models.Product.tags.ilike(like)))
    if category:
        # resolve slug/id exact first (incl. children of parents), fuzzy only as fallback
        exact = db.query(models.Category).filter(
            or_(models.Category.slug == category, models.Category.id == category)).all()
        cat_rows = exact or db.query(models.Category).filter(
            or_(models.Category.slug.ilike(f"%{category}%"),
                models.Category.name.ilike(f"%{category}%"))).all()
        cat_ids = {c.id for c in cat_rows}
        for c in cat_rows:
            for child in db.query(models.Category).filter_by(parent_id=c.id).all():
                cat_ids.add(child.id)
        if cat_ids:
            q = q.filter(models.Product.category_id.in_(cat_ids))
        else:
            q = q.filter(models.Product.category_id == "__none__")
    if brand:
        q = q.join(models.Brand, models.Product.brand_id == models.Brand.id, isouter=True).filter(
            or_(models.Brand.slug == brand, models.Brand.id == brand))
    if min_price is not None:
        q = q.filter(models.Product.price >= min_price)
    if max_price is not None:
        q = q.filter(models.Product.price <= max_price)
    if rating is not None:
        q = q.filter(models.Product.rating_avg >= rating)
    if featured is not None:
        q = q.filter(models.Product.is_featured.is_(bool(featured)))
    sorts = {
        "popular": models.Product.sold_count.desc(),
        "newest": models.Product.created_at.desc(),
        "price_asc": models.Product.price.asc(),
        "price_desc": models.Product.price.desc(),
        "rating": models.Product.rating_avg.desc(),
    }
    q = q.order_by(sorts.get(sort, sorts["popular"]))
    items, page, page_size, total, total_pages = paginate(q, page, page_size)
    if in_stock:
        filtered = [p for p in items if _stock(db, p.id) > 0]
        items = filtered
    return {"items": [serialize_product(db, p) for p in items],
            "page": page, "page_size": page_size, "total": total, "total_pages": total_pages}


def _stock(db: Session, product_id: str) -> int:
    from .helpers import product_stock
    return product_stock(db, product_id)


def get_product(db: Session, pid_or_slug: str):
    p = db.query(models.Product).options(joinedload(models.Product.images),
                                          joinedload(models.Product.variants),
                                          joinedload(models.Product.category),
                                          joinedload(models.Product.brand)).filter(
        or_(models.Product.id == pid_or_slug, models.Product.slug == pid_or_slug),
        models.Product.is_deleted.is_(False)).first()
    if not p:
        return None
    return serialize_product(db, p)


def get_raw_product(db: Session, pid_or_slug: str):
    return db.query(models.Product).filter(
        or_(models.Product.id == pid_or_slug, models.Product.slug == pid_or_slug)).first()


def create_product(db: Session, data: dict):
    p = models.Product(
        name=data["name"], slug=unique_slug(db, models.Product, data["name"]),
        description=data.get("description", ""), category_id=data.get("category_id"),
        brand_id=data.get("brand_id"), price=data.get("price", 0),
        compare_at_price=data.get("compare_at_price", 0),
        is_featured=data.get("is_featured", False),
        specs=__import__("json").dumps(data.get("specs", {})),
        tags=data.get("tags", ""),
    )
    db.add(p)
    db.flush()
    db.add(models.Inventory(product_id=p.id, variant_id=None, quantity=100))
    db.commit()
    db.refresh(p)
    return serialize_product(db, p)


def patch_product(db: Session, p: models.Product, data: dict):
    for k, v in data.items():
        if v is not None and hasattr(p, k):
            setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return serialize_product(db, p)


def related_products(db: Session, product_id: str, limit: int = 8):
    p = db.query(models.Product).filter_by(id=product_id).first()
    if not p:
        return []
    q = db.query(models.Product).options(joinedload(models.Product.images)).filter(
        models.Product.id != product_id, models.Product.is_active.is_(True),
        models.Product.is_deleted.is_(False))
    if p.category_id:
        same = q.filter(models.Product.category_id == p.category_id).limit(limit).all()
        if len(same) >= 4:
            return [serialize_product(db, x) for x in same]
    return [serialize_product(db, x) for x in q.order_by(models.Product.rating_avg.desc()).limit(limit).all()]


def search_suggest(db: Session, q: str, limit: int = 6) -> list[str]:
    if not q:
        return []
    rows = db.query(models.Product.name).filter(models.Product.name.ilike(f"%{q}%")).limit(limit).all()
    return [r[0] for r in rows]
