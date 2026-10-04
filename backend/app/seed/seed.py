"""Deterministic large-scale seed: 100+ categories, 50+ brands, 1000+ products,
2000+ variants, 5000+ reviews, 1000+ users, orders, carts, wishlists, coupons.
Usage:  cd backend && python -m app.seed.seed [--products 1200]
"""
import argparse
import json
import random
import re
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, ".")

from app import models
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.security import hash_password

settings = get_settings()
SEED = 20261004

BRANDS = ["Sony", "Apple", "Samsung", "Nike", "Adidas", "Logitech", "Dell", "HP", "Lenovo",
          "boAt", "JBL", "Canon", "LG", "Xiaomi", "OnePlus", "Puma", "Asus", "Acer", "MSI",
          "Bose", "Sennheiser", "Noise", "Fire-Boltt", "Realme", "Vivo", "Oppo", "Google",
          "Microsoft", "Keychron", "Zebronics", "Philips", "Havells", "Prestige", "Pigeon",
          "Milton", "Wildcraft", "American Tourister", "Fossil", "Casio", "Titan", "Fastrack",
          "Lakme", "Maybelline", "Nivea", "Himalaya", "Dove", "Nykaa", "L'Oreal", "Garnier",
          "Decathlon", "Yonex", "Cosco", "Strauss", "Penguin", "HarperCollins", "Faber-Castell",
          "Ikea", "Wakefit", "Sleepwell", "Urban Ladder", "Portronics", "Ambrane", "Anker"]

TOP_CATS = ["Electronics", "Mobiles", "Laptops", "Computers", "Gaming", "Audio", "Cameras",
            "Fashion", "Men", "Women", "Footwear", "Home", "Kitchen", "Beauty", "Sports",
            "Books", "Accessories", "Smart Home", "Office"]
SUBS = {"Electronics": ["Headphones", "Speakers", "Wearables", "Drones", "Chargers", "Cables"],
        "Mobiles": ["Smartphones", "Feature Phones", "Phone Cases", "Screen Guards", "Power Banks"],
        "Laptops": ["Ultrabooks", "Gaming Laptops", "2-in-1 Laptops", "MacBooks", "Chromebooks"],
        "Computers": ["Monitors", "Keyboards", "Mice", "SSDs", "Printers", "Webcams"],
        "Gaming": ["Consoles", "Controllers", "Gaming Chairs", "VR Headsets", "Game Titles"],
        "Audio": ["Earbuds", "Soundbars", "Microphones", "Turntables", "Receivers"],
        "Cameras": ["Mirrorless", "DSLR", "Action Cameras", "Lenses", "Tripods"],
        "Fashion": ["T-Shirts", "Jeans", "Jackets", "Kurtas", "Sarees"],
        "Men": ["Shirts", "Trousers", "Suits", "Wallets", "Belts"],
        "Women": ["Dresses", "Handbags", "Jewellery", "Footwear-W", "Makeup Kits"],
        "Footwear": ["Running Shoes", "Sneakers", "Sandals", "Formal Shoes", "Boots"],
        "Home": ["Bedsheets", "Lamps", "Curtains", "Wall Art", "Storage"],
        "Kitchen": ["Cookware", "Mixer Grinders", "Air Fryers", "Lunch Boxes", "Knives"],
        "Beauty": ["Skincare", "Haircare", "Fragrances", "Grooming", "Bath Essentials"],
        "Sports": ["Fitness Bands", "Dumbbells", "Yoga Mats", "Cricket", "Football"],
        "Books": ["Fiction", "Non-Fiction", "Comics", "Academic", "Children"],
        "Accessories": ["Backpacks", "Sunglasses", "Watches", "Wallets-A", "Caps"],
        "Smart Home": ["Smart Bulbs", "Security Cameras", "Video Doorbells", "Smart Plugs", "Hubs"],
        "Office": ["Notebooks", "Pens", "Desk Organizers", "Office Chairs", "Shredders"]}
EXTRA_CATS = ["Clearance", "New Arrivals", "Bestsellers", "Gift Cards", "Refurbished",
              "Pet Supplies", "Baby Care", "Grocery", "Automotive", "Tools", "Garden",
              "Stationery", "Music", "Movies", "Party Supplies"]

# (category_hint, name_template, brands, price_lo, price_hi)
TEMPLATES = [
    ("Headphones", "{B} WH-1000XM6 Wireless Noise Cancelling Headphones", ["Sony", "Bose", "Sennheiser"], 18000, 35000),
    ("Earbuds", "{B} True Wireless Earbuds with ANC", ["boAt", "Noise", "JBL", "OnePlus", "Realme"], 1500, 9000),
    ("Smartphones", "{B} Galaxy S26 Ultra 5G (12GB, 256GB)", ["Samsung", "OnePlus", "Xiaomi", "Vivo"], 35000, 130000),
    ("Smartphones", "{B} iPhone 17 Pro (256GB)", ["Apple"], 80000, 170000),
    ("Smartphones", "{B} Pixel 10 Pro 5G (128GB)", ["Google"], 70000, 110000),
    ("Ultrabooks", "{B} MacBook Air M4 (16GB, 512GB)", ["Apple"], 95000, 150000),
    ("Ultrabooks", "{B} XPS 14 OLED Laptop (Ultra 7, 16GB)", ["Dell", "HP", "Lenovo", "Asus"], 65000, 140000),
    ("Gaming Laptops", "{B} ROG Strix G16 RTX 4060 Gaming Laptop", ["Asus", "MSI", "Acer", "Lenovo"], 75000, 180000),
    ("Monitors", "{B} UltraSharp 32 4K USB-C Monitor", ["Dell", "LG", "Samsung", "BenQ"], 22000, 75000),
    ("Mice", "{B} MX Master 4 Wireless Mouse", ["Logitech", "HP", "Dell"], 4500, 12000),
    ("Keyboards", "{B} K8 Pro Mechanical Keyboard", ["Keychron", "Logitech", "Zebronics"], 3500, 15000),
    ("Running Shoes", "{B} Air Max 2026 Running Shoes", ["Nike", "Adidas", "Puma", "Asics"], 4000, 18000),
    ("Sneakers", "{B} Ultraboost Light Sneakers", ["Adidas", "Nike", "Puma"], 6000, 22000),
    ("Mirrorless", "{B} EOS R50 Mirrorless Camera with 18-45mm", ["Canon", "Sony", "Nikon"], 55000, 120000),
    ("Speakers", "{B} Flip 6 Portable Bluetooth Speaker", ["JBL", "boAt", "Sony", "Philips"], 3000, 15000),
    ("Wearables", "{B} Galaxy Watch 7 BT (44mm)", ["Samsung", "Apple", "Noise", "Fire-Boltt"], 2500, 45000),
    ("Cookware", "{B} Tri-Ply Stainless Cookware Set (5pc)", ["Prestige", "Pigeon", "Hawkins"], 2500, 12000),
    ("Air Fryers", "{B} Digital Air Fryer 5.5L", ["Philips", "Havells", "Pigeon"], 6000, 16000),
    ("Skincare", "{B} Vitamin C Face Serum 30ml", ["Lakme", "Garnier", "Himalaya", "Dot & Key"], 300, 1500),
    ("Fragrances", "{B} Eau De Parfum 100ml", ["Fogg", "Wild Stone", "Nivea"], 400, 3500),
    ("Backpacks", "{B} 32L Laptop Backpack", ["American Tourister", "Wildcraft", "Nike"], 1200, 6000),
    ("Watches", "{B} Chronograph Leather Watch", ["Fossil", "Casio", "Titan", "Fastrack"], 2500, 25000),
    ("Fitness Bands", "{B} Smart Fitness Band Pro", ["Noise", "Fire-Boltt", "Xiaomi"], 1500, 6000),
    ("Yoga Mats", "{B} 6mm Anti-Skid Yoga Mat", ["Strauss", "Boldfit", "Cosco"], 500, 2500),
    ("Fiction", "{B} Bestseller Paperback Collection", ["Penguin", "HarperCollins"], 200, 1200),
    ("Smart Bulbs", "{B} 9W Smart WiFi Bulb (16M colors)", ["Philips", "Havells", "Wipro"], 600, 2500),
    ("Security Cameras", "{B} 360° WiFi Home Camera", ["Xiaomi", "TP-Link", "Qubo"], 1800, 6000),
    ("Consoles", "{B} PlayStation 5 Slim Console", ["Sony"], 45000, 60000),
    ("Controllers", "{B} Wireless Pro Controller", ["Sony", "Microsoft", "Logitech"], 3500, 8000),
    ("T-Shirts", "{B} Pure Cotton Oversized T-Shirt", ["Nike", "Adidas", "Puma", "H&M"], 400, 2000),
    ("Jeans", "{B} Slim-Fit Stretch Jeans", ["Levis", "Pepe", "Wrangler"], 1200, 4500),
    ("Dresses", "{B} Floral Summer Midi Dress", ["Zara", "H&M", "Myntra"], 900, 3500),
    ("Power Banks", "{B} 20000mAh Fast-Charge Power Bank", ["Ambrane", "Anker", "Portronics", "Xiaomi"], 1200, 3500),
    ("SSDs", "{B} 1TB NVMe Gen4 SSD", ["Samsung", "Crucial", "WD"], 5000, 12000),
    ("Lamps", "{B} Minimalist LED Table Lamp", ["Philips", "Havells", "Ikea"], 800, 4000),
    ("Bedsheets", "{B} 210TC Cotton King Bedsheet", ["Sleepwell", "Wakefit", "Bombay Dyeing"], 700, 3000),
]

COLORS = ["Midnight Black", "Arctic White", "Ocean Blue", "Forest Green", "Sunset Red",
          "Graphite Grey", "Rose Gold", "Navy", "Beige", "Charcoal"]
SIZES = {"Footwear": ["UK 6", "UK 7", "UK 8", "UK 9", "UK 10"],
         "Fashion": ["S", "M", "L", "XL"], "default": ["Standard", "Large"]}
STORAGE = ["128GB", "256GB", "512GB", "1TB"]

REVIEW_TITLES = ["Excellent product", "Value for money", "Exceeded expectations", "Good, with minor flaws",
                 "Highly recommended", "Solid build quality", "Perfect for my needs", "Decent for the price",
                 "Superb!", "Not bad at all", "Five stars", "Works as advertised"]
REVIEW_BODIES = [
    "Delivery was quick and packaging was excellent. The product matches the description perfectly.",
    "Using it for a few weeks now. Performance is consistent and quality feels premium for this price.",
    "Bought this after comparing several options. Genuinely happy — does exactly what it promises.",
    "Good overall. Setup took a few minutes. Would have liked more colour options, but no complaints.",
    "Authentic product, sealed pack, GST invoice included. Customer support helped with a small query.",
    "Gifted this to a family member and they love it. Battery/packaging/quality all top notch.",
    "Does the job well for daily use. Shipping took a day longer than estimated but worth the wait.",
]


def slugify(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:120]


def run(products_target: int = 1200, users_target: int = 1000):
    random.seed(SEED)
    try:
        from faker import Faker
        fake = Faker("en_IN")
        fake.seed_instance(SEED)
    except Exception:
        fake = None
    db = SessionLocal()
    try:
        # wipe (dev-friendly)
        for m in [models.AgentMessage, models.AgentConversation, models.UserEvent,
                  models.SearchHistory, models.Notification, models.Review, models.CouponUsage,
                  models.Coupon, models.Shipment, models.Payment, models.OrderItem, models.Order,
                  models.WishlistItem, models.Wishlist, models.CartItem, models.Cart,
                  models.InventoryTransaction, models.Inventory, models.ProductImage,
                  models.ProductVariant, models.Product, models.Address, models.User,
                  models.Category, models.Brand]:
            db.query(m).delete()
        db.commit()

        # brands
        brand_objs = []
        for name in BRANDS:
            b = models.Brand(id=str(uuid.uuid4()), name=name, slug=slugify(name),
                             description=f"Official {name} store.", logo_url="")
            db.add(b)
            brand_objs.append(b)
        db.commit()
        brand_by_name = {b.name: b for b in brand_objs}

        # categories: tops + subs + extras => 19 + ~100 + 15 > 100
        cat_objs, cat_by_name = [], {}
        for t in TOP_CATS:
            c = models.Category(id=str(uuid.uuid4()), name=t, slug=slugify(t),
                                description=f"Shop {t}.",
                                image_url=f"https://picsum.photos/seed/cat-{slugify(t)}/400/300")
            db.add(c)
            cat_objs.append(c)
            cat_by_name[t] = c
        db.commit()
        for top, subs in SUBS.items():
            parent = cat_by_name[top]
            for s in subs:
                c = models.Category(id=str(uuid.uuid4()), name=s, slug=slugify(f"{top} {s}"),
                                    description=f"Shop {s} in {top}.", parent_id=parent.id,
                                    image_url=f"https://picsum.photos/seed/cat-{slugify(s)}/400/300")
                db.add(c)
                cat_objs.append(c)
                cat_by_name[s] = c
        for e in EXTRA_CATS:
            c = models.Category(id=str(uuid.uuid4()), name=e, slug=slugify(e),
                                description=f"Shop {e}.",
                                image_url=f"https://picsum.photos/seed/cat-{slugify(e)}/400/300")
            db.add(c)
            cat_objs.append(c)
        db.commit()
        leaf_cats = [c for c in cat_objs if c.parent_id]

        # users (single shared hash: same demo password for all seed users)
        seed_pw = hash_password(settings.demo_password)
        users = []
        for i in range(users_target):
            name = fake.name() if fake else f"Customer {i+1}"
            email = f"user{i+1:04d}@example.com"
            users.append(models.User(id=str(uuid.uuid4()), email=email,
                                     password_hash=seed_pw,
                                     full_name=name, role="customer"))
        users.append(models.User(id=str(uuid.uuid4()), email=settings.demo_customer_email,
                                 password_hash=seed_pw,
                                 full_name="Demo Customer", role="customer"))
        users.append(models.User(id=str(uuid.uuid4()), email=settings.demo_admin_email,
                                 password_hash=seed_pw,
                                 full_name="Store Admin", role="admin"))
        for m in range(3):
            users.append(models.User(id=str(uuid.uuid4()), email=f"manager{m+1}@example.com",
                                     password_hash=seed_pw,
                                     full_name=f"Manager {m+1}", role="manager"))
        db.add_all(users)
        db.commit()

        # products
        products, variants, images, invs = [], [], [], []
        for i in range(products_target):
            t = TEMPLATES[i % len(TEMPLATES)]
            cat_hint, tmpl, brand_pool, lo, hi = t
            bname = random.choice(brand_pool)
            year = random.choice(["2024", "2025", "2026", "Pro", "Max", "Plus", "Lite"])
            name = tmpl.format(B=bname)
            if random.random() < 0.45:
                name = f"{name} {year}".replace("  ", " ")
            # ensure uniqueness
            name = f"{name} · Gen {i//len(TEMPLATES)+1}" if i >= len(TEMPLATES) else name
            cat = cat_by_name.get(cat_hint) or random.choice(leaf_cats)
            brand = brand_by_name.get(bname) or random.choice(brand_objs)
            price = round(random.uniform(lo, hi), 0)
            mrp = price if random.random() < 0.35 else round(price * random.uniform(1.05, 1.6), 0)
            rating = round(random.uniform(3.4, 4.9), 1)
            rc = int(random.uniform(5, 2500))
            pid = str(uuid.uuid4())
            p = models.Product(id=pid, name=name, slug=f"{slugify(name)}-{i}",
                               description=f"{name}. Premium {cat.name.lower()} from {bname} with warranty, GST invoice and 7-day replacement.",
                               category_id=cat.id, brand_id=brand.id, price=price,
                               compare_at_price=mrp, rating_avg=rating, rating_count=rc,
                               sold_count=int(random.uniform(0, 5000)),
                               view_count=int(random.uniform(50, 30000)),
                               is_featured=random.random() < 0.08,
                               specs=json.dumps({"brand": bname, "category": cat.name,
                                                  "warranty": "1 year", "in_box": "1 unit + manual"}),
                               tags=f"{bname},{cat.name},{cat_hint}")
            products.append(p)
            # images (2-3)
            for k in range(random.choice([2, 2, 3])):
                images.append(models.ProductImage(id=str(uuid.uuid4()), product_id=pid,
                                                  url=f"https://picsum.photos/seed/{pid[:8]}-{k}/800/800",
                                                  alt=name, position=k))
            # variants 1-3
            nvar = random.choice([1, 2, 2, 3])
            for v in range(nvar):
                color = random.choice(COLORS)
                if cat_hint in ("Smartphones", "Ultrabooks", "Gaming Laptops", "SSDs"):
                    size = random.choice(STORAGE)
                elif cat.name in SIZES or cat_hint in SIZES:
                    size = random.choice(SIZES.get(cat.name, SIZES.get(cat_hint, SIZES["default"])))
                else:
                    size = random.choice(SIZES["default"]) if v else "Standard"
                vid = str(uuid.uuid4())
                variants.append(models.ProductVariant(
                    id=vid, product_id=pid, sku=f"SKU-{pid[:6].upper()}-{v}",
                    name=f"{color} / {size}", color=color, size=size,
                    price_override=round(price * random.uniform(0.95, 1.25), 0) if v else None))
                qty = int(random.uniform(0, 120))
                invs.append(models.Inventory(id=str(uuid.uuid4()), product_id=pid, variant_id=vid,
                                             quantity=qty, low_stock_threshold=5))
            # base inventory row
            invs.append(models.Inventory(id=str(uuid.uuid4()), product_id=pid, variant_id=None,
                                         quantity=int(random.uniform(0, 200)), low_stock_threshold=5))
        db.add_all(products)
        db.commit()
        db.add_all(variants)
        db.add_all(images)
        db.add_all(invs)
        db.commit()
        print(f"seeded {len(products)} products, {len(variants)} variants, {len(users)} users, {len(cat_objs)} categories")

        # reviews 5000+ (dedupe pairs in-memory: unique(product,user))
        seen_pairs: set[tuple[str, str]] = set()
        revs = []
        attempts = 0
        while len(revs) < 5500 and attempts < 30000:
            attempts += 1
            p = random.choice(products)
            u = random.choice(users)
            key = (p.id, u.id)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            r = random.choices([5, 4, 3, 2, 1], weights=[45, 30, 12, 6, 7])[0]
            revs.append(models.Review(id=str(uuid.uuid4()), product_id=p.id, user_id=u.id,
                                      rating=r, title=random.choice(REVIEW_TITLES),
                                      body=random.choice(REVIEW_BODIES),
                                      is_verified_purchase=random.random() < 0.7,
                                      helpful_count=int(random.uniform(0, 120))))
        db.add_all(revs)
        db.commit()
        print(f"reviews inserted: {len(revs)}")
        # recompute ratings
        from sqlalchemy import func
        for p in products:
            rows = db.query(models.Review.rating).filter_by(product_id=p.id).all()
            if rows:
                p.rating_avg = round(sum(r[0] for r in rows) / len(rows), 2)
                p.rating_count = len(rows)
        db.commit()
        print("reviews done")

        # coupons
        coupons = [
            ("WELCOME10", "10% off first order", "percent", 10, 499, 500),
            ("FESTIVE20", "20% off festive sale", "percent", 20, 999, 1500),
            ("FLAT500", "Flat ₹500 off above ₹4,999", "flat", 500, 4999, None),
            ("FREESHIP", "Free shipping unlocked", "flat", 49, 499, None),
            ("TECH15", "15% off electronics", "percent", 15, 1999, 2000),
        ]
        for code, desc, typ, val, mov, mx in coupons:
            db.add(models.Coupon(id=str(uuid.uuid4()), code=code, description=desc,
                                 discount_type=typ, discount_value=val,
                                 min_order_value=mov, max_discount=mx, usage_limit=100000))
        db.commit()

        # orders + carts + wishlists for a subset
        import math
        n_orders = 0
        for u in users[:400]:
            if u.role != "customer":
                continue
            # wishlist
            w = models.Wishlist(id=str(uuid.uuid4()), user_id=u.id)
            db.add(w)
            db.flush()
            for p in random.sample(products, random.randint(0, 5)):
                db.add(models.WishlistItem(id=str(uuid.uuid4()), wishlist_id=w.id, product_id=p.id))
            # cart (some users)
            if random.random() < 0.35:
                c = models.Cart(id=str(uuid.uuid4()), user_id=u.id)
                db.add(c)
                db.flush()
                for p in random.sample(products, random.randint(1, 3)):
                    db.add(models.CartItem(id=str(uuid.uuid4()), cart_id=c.id,
                                           product_id=p.id, quantity=random.randint(1, 2)))
            # orders
            for _ in range(random.randint(0, 3)):
                ostatus = random.choice(["delivered", "delivered", "delivered", "shipped",
                                         "processing", "confirmed", "cancelled"])
                items = random.sample(products, random.randint(1, 4))
                sub = sum(float(p.price) for p in items)
                o = models.Order(id=str(uuid.uuid4()),
                                 order_number="NC" + uuid.uuid4().hex[:10].upper(),
                                 user_id=u.id, status=ostatus, subtotal=sub, discount=0,
                                 shipping=0 if sub >= 999 else 49, tax=round(sub * 0.18, 2),
                                 total=round(sub * 1.18, 2),
                                 shipping_address=json.dumps({"line1": "221 MG Road", "city": "Bengaluru"}),
                                 payment_status="paid" if ostatus != "cancelled" else "refunded",
                                 created_at=datetime.utcnow() - timedelta(days=random.randint(0, 90)))
                db.add(o)
                db.flush()
                for p in items:
                    db.add(models.OrderItem(id=str(uuid.uuid4()), order_id=o.id, product_id=p.id,
                                            product_name=p.name, quantity=1,
                                            unit_price=float(p.price), total_price=float(p.price)))
                db.add(models.Payment(id=str(uuid.uuid4()), order_id=o.id, provider="mock",
                                      status="paid", amount=o.total))
                db.add(models.Shipment(id=str(uuid.uuid4()), order_id=o.id,
                                       tracking_number="TRK" + o.order_number,
                                       status=ostatus if ostatus != "confirmed" else "processing",
                                       estimated_delivery=datetime.utcnow() + timedelta(days=5)))
                n_orders += 1
        # demo customer gets a cart + wishlist + 2 orders
        demo = next(u for u in users if u.email == settings.demo_customer_email)
        w = models.Wishlist(id=str(uuid.uuid4()), user_id=demo.id)
        db.add(w)
        db.flush()
        for p in products[:6]:
            db.add(models.WishlistItem(id=str(uuid.uuid4()), wishlist_id=w.id, product_id=p.id))
        db.commit()
        print(f"orders: {n_orders}")
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", type=int, default=1200)
    ap.add_argument("--users", type=int, default=1000)
    args = ap.parse_args()
    Base.metadata.create_all(bind=engine)
    run(args.products, args.users)
