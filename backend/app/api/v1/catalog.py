"""Catalog routers: products, categories, brands, search."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ... import models
from ...database import get_db
from ...deps import get_optional_user, require_roles
from ...schemas import BrandOut, CategoryOut, ProductCreateIn, ProductOut, ProductPatchIn
from ...services import product_service as svc
from ...services.helpers import paginate, unique_slug
from ...services.shop_service import log_event

products_router = APIRouter()
categories_router = APIRouter()
brands_router = APIRouter()
search_router = APIRouter()


@products_router.get("", summary="List products with filters")
def list_products(page: int = 1, page_size: int = 24, search: str = "",
                  category: str = "", brand: str = "", min_price: float | None = None,
                  max_price: float | None = None, rating: float | None = None,
                  sort: str = "popular", in_stock: bool | None = None,
                  featured: bool | None = None, db: Session = Depends(get_db)):
    return svc.list_products(db, page, page_size, search, category, brand,
                             min_price, max_price, rating, sort, in_stock, featured)


@products_router.get("/trending", summary="Trending products")
def trending(db: Session = Depends(get_db)):
    return svc.list_products(db, 1, 12, sort="popular")["items"]


@products_router.get("/deals", summary="Discounted products")
def deals(db: Session = Depends(get_db)):
    q = db.query(models.Product).filter(models.Product.compare_at_price > models.Product.price,
                                        models.Product.is_active.is_(True))
    items, *_ = paginate(q.order_by(models.Product.sold_count.desc()), 1, 12) if False else ([], 1, 12, 0, 1)
    allp = svc.list_products(db, 1, 100, sort="popular")["items"]
    return [p for p in allp if p["discount_pct"] > 0][:12]


@products_router.get("/{pid_or_slug}", summary="Product detail")
def get_product(pid_or_slug: str, db: Session = Depends(get_db),
                user=Depends(get_optional_user)):
    p = svc.get_product(db, pid_or_slug)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    raw = svc.get_raw_product(db, pid_or_slug)
    if raw:
        raw.view_count += 1
        db.commit()
        log_event(db, user.id if user else None, "view", raw.id)
    return p


@products_router.get("/{pid_or_slug}/related", summary="Related products")
def related(pid_or_slug: str, db: Session = Depends(get_db)):
    raw = svc.get_raw_product(db, pid_or_slug)
    if not raw:
        raise HTTPException(status_code=404, detail="Product not found")
    return svc.related_products(db, raw.id)


@products_router.post("", status_code=201, summary="Create product (admin)")
def create_product(data: ProductCreateIn, db: Session = Depends(get_db),
                   admin=Depends(require_roles("admin", "manager"))):
    return svc.create_product(db, data.model_dump())


@products_router.patch("/{pid}", summary="Update product (admin)")
def patch_product(pid: str, data: ProductPatchIn, db: Session = Depends(get_db),
                  admin=Depends(require_roles("admin", "manager"))):
    p = db.get(models.Product, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return svc.patch_product(db, p, data.model_dump(exclude_unset=True))


@products_router.delete("/{pid}", summary="Soft-delete product (admin)")
def delete_product(pid: str, db: Session = Depends(get_db),
                    admin=Depends(require_roles("admin", "manager"))):
    p = db.get(models.Product, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    p.is_deleted = True
    p.is_active = False
    db.commit()
    return {"ok": True}


@categories_router.get("", summary="List categories")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(models.Category).filter_by(is_active=True).order_by(models.Category.name).all()
    counts = {}
    for (cid, n) in db.query(models.Product.category_id, models.Product.id).filter(
            models.Product.is_active.is_(True)).all():
        counts[cid] = counts.get(cid, 0) + 1
    out = []
    for c in cats:
        out.append({"id": c.id, "name": c.name, "slug": c.slug, "description": c.description,
                    "image_url": c.image_url or f"https://picsum.photos/seed/{c.slug}/400/300",
                    "parent_id": c.parent_id, "product_count": counts.get(c.id, 0)})
    return out


@categories_router.get("/{slug}", summary="Category detail")
def get_category(slug: str, db: Session = Depends(get_db)):
    c = db.query(models.Category).filter(
        (models.Category.slug == slug) | (models.Category.id == slug)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"id": c.id, "name": c.name, "slug": c.slug, "description": c.description,
            "image_url": c.image_url, "parent_id": c.parent_id, "product_count": 0}


@brands_router.get("", summary="List brands")
def list_brands(db: Session = Depends(get_db)):
    brands = db.query(models.Brand).filter_by(is_active=True).order_by(models.Brand.name).all()
    return [{"id": b.id, "name": b.name, "slug": b.slug, "description": b.description,
             "logo_url": b.logo_url, "product_count": b.product_count} for b in brands]


@search_router.get("", summary="Backend-powered search")
def search(q: str = "", page: int = 1, page_size: int = 24, category: str = "",
           brand: str = "", min_price: float | None = None, max_price: float | None = None,
           rating: float | None = None, sort: str = "popular",
           db: Session = Depends(get_db), user=Depends(get_optional_user)):
    res = svc.list_products(db, page, page_size, q, category, brand, min_price, max_price, rating, sort)
    try:
        db.add(models.SearchHistory(user_id=user.id if user else None, query=q,
                                    results_count=res["total"]))
        db.commit()
    except Exception:
        pass
    res["suggestions"] = svc.search_suggest(db, q)
    return res


@search_router.get("/suggest", summary="Autocomplete suggestions")
def suggest(q: str = Query(default="", min_length=1), db: Session = Depends(get_db)):
    return {"suggestions": svc.search_suggest(db, q)}
