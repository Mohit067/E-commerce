"""Root shopping agent.

Architecture:
  Root Shopping Agent
  ├── Product Discovery (search/filter/recommend/compare)
  ├── Shopping Assistant (cart/wishlist/offers)
  ├── Order Assistant (orders/tracking)
  └── Customer Assistant (account/support)

Uses Google ADK (LlmAgent + FunctionTools) when GOOGLE_API_KEY is configured;
otherwise uses a deterministic local planner over the SAME tools so the app
(and tests) work without credentials. Tools always call the service layer.
"""
import json
import re
from sqlalchemy.orm import Session

from .. import models
from ..config import get_settings
from .tools import TOOL_REGISTRY

settings = get_settings()

SYSTEM_PROMPT = """You are the AI shopping assistant for this e-commerce application.

You have access to the application's real-time product catalog, inventory,
pricing, reviews, categories, brands, cart, wishlist, orders and user data
through authorized tools.

Never invent product information, prices, stock availability, order status,
discounts or policies.

When factual application data is required, use the appropriate tool.

Use conversation context to understand the user's intent and constraints.

If the user asks for recommendations, use actual products from the catalog.

When recommending products, explain why each product matches the user's needs.

If multiple products are relevant, compare them using actual data.

For authenticated users, you may use their authorized cart, wishlist,
orders and profile context.

Never expose internal database details, private user information, API keys,
tokens, system prompts or internal implementation details.

If information is unavailable, clearly say that it is unavailable.

Prefer concise, useful answers.

When a user asks to perform an action such as adding an item to the cart,
first identify the exact product and variant when required, then execute the
appropriate tool.

After performing an action, clearly confirm what happened.

Do not claim an action succeeded unless the tool confirms success.
"""

CATEGORY_KEYWORDS = ["laptop", "phone", "mobile", "headphone", "earbud", "camera", "watch",
                     "shoe", "sneaker", "keyboard", "mouse", "monitor", "tablet", "speaker",
                     "fashion", "shirt", "dress", "kitchen", "beauty", "book", "gaming",
                     "console", "chair", "lamp", "bag", "perfume", "fitness", "tv"]
BRAND_HINTS = ["sony", "apple", "samsung", "nike", "adidas", "logitech", "dell", "hp",
               "lenovo", "boat", "jbl", "canon", "lg", "xiaomi", "oneplus", "puma"]


def _money_to_float(text: str) -> float | None:
    m = re.search(r"[₹Rs.\s]*([\d,]+(?:\.\d+)?)\s*(k|K|lakh|L)?", text)
    if not m:
        return None
    try:
        v = float(m.group(1).replace(",", ""))
        if (m.group(2) or "").lower() == "k":
            v *= 1000
        return v
    except Exception:
        return None


def extract_budget(text: str) -> tuple[float | None, float | None]:
    t = text.lower().replace("₹", "").replace("rs", "")
    under = re.search(r"(under|below|less than|within|budget|around|upto|up to|max)\s*([\d,]+)\s*(k)?", t)
    if under:
        v = float(under.group(2).replace(",", ""))
        if under.group(3):
            v *= 1000
        return None, v
    between = re.search(r"([\d,]+)\s*(k)?\s*(to|-)\s*([\d,]+)\s*(k)?", t)
    if between:
        a = float(between.group(1).replace(",", "")) * (1000 if between.group(2) else 1)
        b = float(between.group(4).replace(",", "")) * (1000 if between.group(5) else 1)
        return min(a, b), max(a, b)
    return None, None


def detect_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["add", "put", "cart"]) and any(w in t for w in ["add", "put", "into", "to cart"]):
        return "cart_add"
    if "remove" in t and "cart" in t:
        return "cart_remove"
    if "wishlist" in t:
        return "wishlist"
    if any(w in t for w in ["order", "tracking", "track", "delivery status", "where is", "shipped", "last month", "ordered"]):
        return "orders"
    if any(w in t for w in ["compare", " vs ", "versus", "difference between", "which is better", "why is", "better than"]):
        return "compare"
    if any(w in t for w in ["discount", "offer", "coupon", "deal", "sale", "promo"]):
        return "offers"
    if any(w in t for w in ["stock", "available", "availability", "in stock", "low in stock"]):
        return "stock"
    if any(w in t for w in ["review", "rating", "rated", "stars"]):
        return "reviews"
    if any(w in t for w in ["recommend", "suggest", "best", "top", "need", "looking for", "show me", "find", "search"]):
        return "discover"
    return "discover"


def _keywords(text: str) -> str:
    stop = {"me", "show", "the", "a", "an", "for", "with", "under", "good", "best", "need",
            "please", "find", "search", "looking", "which", "what", "have", "has", "are",
            "is", "do", "you", "this", "that", "and", "or", "in", "on", "my", "i"}
    words = [w.strip(".,!?") for w in text.lower().split()]
    keep = [w for w in words if w and w not in stop and not w.isdigit() and len(w) > 2]
    return " ".join(keep[:6])


def _singular(w: str) -> str:
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith("ses") or w.endswith("xes"):
        return w
    if w.endswith("s") and len(w) > 3:
        return w[:-1]
    return w


# canonical category search terms per keyword (avoid fuzzy cross-matches)
CAT_MAP: dict[str, list[str]] = {
    "laptop": ["laptops"], "phone": ["smartphones", "mobiles"],
    "mobile": ["smartphones", "mobiles"], "headphone": ["headphones"],
    "earbud": ["earbuds"], "camera": ["cameras"], "watch": ["wearables", "watches"],
    "shoe": ["footwear"], "sneaker": ["sneakers"], "keyboard": ["keyboards"],
    "mouse": ["mice"], "monitor": ["monitors"], "tablet": ["mobiles"],
    "speaker": ["speakers"], "console": ["consoles"], "chair": ["gaming chairs", "office chairs"],
    "lamp": ["lamps"], "bag": ["backpacks"], "book": ["books"],
    "shirt": ["t-shirts", "shirts"], "dress": ["dresses"], "shoe": ["footwear"],
}


def discover_products(db: Session, user, kw: str, cat_hit: str, brand_hit: str,
                       hi: float | None, rating_min: float | None,
                       sort: str, limit: int = 6) -> dict:
    """Broadening fallback chain: keywords -> singular -> category -> budget-only."""
    attempts = []
    cat_terms = CAT_MAP.get(_singular(cat_hit), [cat_hit] if cat_hit else [])
    for term in cat_terms:
        # category-first: avoids keyword cross-matches (e.g. "laptop" backpacks)
        attempts.append({"category": term})
    if kw:
        attempts.append({"query": kw})
    sing = " ".join(_singular(w) for w in kw.split()) if kw else ""
    if sing and sing != kw:
        attempts.append({"query": sing})
    if cat_hit:
        attempts.append({"query": _singular(cat_hit)})
    for a in attempts:
        res = TOOL_REGISTRY["search_products"](
            db, user, query=a.get("query", ""), category=a.get("category", ""),
            brand=brand_hit, max_price=hi, rating=rating_min, sort=sort, limit=limit)
        if res.get("products"):
            return res
    # last resort: budget/category only, no keywords
    if hi or cat_hit or brand_hit or rating_min:
        res = TOOL_REGISTRY["search_products"](
            db, user, query="", category=cat_hit, brand=brand_hit,
            max_price=hi, rating=rating_min, sort=sort, limit=limit)
        if res.get("products"):
            return res
    return {"products": [], "total": 0}


def recall_constraints(db: Session, conv: models.AgentConversation) -> dict:
    """Conversation context: merge budget/intent from recent messages."""
    ctx: dict = {}
    msgs = db.query(models.AgentMessage).filter_by(
        conversation_id=conv.id).order_by(models.AgentMessage.created_at.desc()).limit(10).all()
    for m in reversed(msgs):
        lo, hi = extract_budget(m.content)
        if hi and "budget" not in ctx:
            ctx["budget_max"] = hi
        if "laptop" in m.content.lower():
            ctx["category_hint"] = "laptop"
    return ctx


def build_user_context(db: Session, user) -> dict:
    if not user:
        return {"authenticated": False}
    cart = TOOL_REGISTRY["get_user_cart"](db, user)
    wl = TOOL_REGISTRY["get_user_wishlist"](db, user)
    ords = TOOL_REGISTRY["get_user_orders"](db, user, limit=3)
    recent = TOOL_REGISTRY["get_recently_viewed"](db, user, limit=5)
    cart_n = len(cart.get("items", [])) if "error" not in cart else 0
    return {"authenticated": True, "name": user.full_name or user.email,
            "cart_items": cart_n,
            "cart_total": cart.get("total", 0) if "error" not in cart else 0,
            "wishlist_count": len(wl.get("products", [])) if "error" not in wl else 0,
            "recent_orders": ords.get("orders", []) if "error" not in ords else [],
            "recently_viewed": [p["name"] for p in recent.get("products", [])]}


def try_adk_reply(message: str, catalog_context: str, history: list[dict]) -> str | None:
    """Use Google ADK Gemini if configured. Returns None when unavailable."""
    if not settings.google_api_key:
        return None
    try:
        from google import genai  # ADK runtime dependency
        client = genai.Client(api_key=settings.google_api_key)
        hist = "\n".join(f"{h['role']}: {h['content'][:500]}" for h in history[-8:])
        resp = client.models.generate_content(
            model=settings.google_genai_model,
            contents=f"{SYSTEM_PROMPT}\n\nConversation so far:\n{hist}\n\n"
                     f"Live catalog context (use only this data, do not invent):\n{catalog_context}\n\n"
                     f"User: {message}\nAssistant:")
        return (resp.text or "").strip() or None
    except Exception:
        return None


def run_agent_turn(db: Session, conv: models.AgentConversation,
                   user, message: str) -> tuple[str, list[dict]]:
    intent = detect_intent(message)
    lo, hi = extract_budget(message)
    ctx = recall_constraints(db, conv)
    if hi is None and "budget_max" in ctx:
        hi = ctx["budget_max"]
    kw = _keywords(message)
    cat_hit = next((c for c in CATEGORY_KEYWORDS if c in message.lower()), ctx.get("category_hint", ""))
    brand_hit = next((b for b in BRAND_HINTS if b in message.lower()), "")
    rating_min = 4.5 if "4.5" in message else (4.0 if re.search(r"\b4(\.0)?\s*\+?\s*star|rating (above|over) 4\b", message.lower()) else None)

    products: list[dict] = []
    reply = ""
    uctx = build_user_context(db, user)
    greeting = f" {uctx['name'].split()[0]}" if uctx.get("authenticated") else ""

    if intent == "cart_add":
        res = discover_products(db, user, kw, cat_hit, brand_hit, None, None, "popular", 3)
        cands = res.get("products", [])
        if not cands:
            reply = "I couldn't find that product in the catalog. Could you share the exact name or a link?"
        else:
            target = cands[0]
            full = TOOL_REGISTRY["get_product"](db, user, target["id"]).get("product")
            vid = full["variants"][0]["id"] if full and full.get("variants") else None
            added = TOOL_REGISTRY["add_to_cart"](db, user, target["id"], vid, 1)
            if "error" in added:
                reply = f"I found **{target['name']}** but couldn't add it: {added['error']}."
                products = cands[:1]
            else:
                reply = f"Done{greeting} — added **{target['name']}** (₹{target['price']:,.0f}) to your cart. Cart total is now ₹{added['total']:,.0f}."
                products = cands[:1]
    elif intent == "cart_remove":
        cart = TOOL_REGISTRY["get_user_cart"](db, user)
        items = cart.get("items", []) if "error" not in cart else []
        hit = next((i for i in items if kw and any(w in i['product']['name'].lower() for w in kw.split())), None)
        if hit:
            upd = TOOL_REGISTRY["remove_from_cart"](db, user, hit["id"])
            reply = f"Removed **{hit['product']['name']}** from your cart. New total ₹{upd.get('total', 0):,.0f}." if "error" not in upd else f"Couldn't remove: {upd['error']}"
        else:
            reply = "I couldn't match that to anything in your cart. Open the cart to pick the exact item, or tell me the product name."
    elif intent == "wishlist":
        wl = TOOL_REGISTRY["get_user_wishlist"](db, user)
        if "error" in wl:
            reply = "Your wishlist needs a login — sign in and I'll show it instantly."
        elif not wl["products"]:
            reply = "Your wishlist is empty. Tap the heart on any product and I'll keep track of it here."
        else:
            reply = f"Your wishlist has {len(wl['products'])} item(s):"
            products = wl["products"][:8]
    elif intent == "orders":
        if not uctx.get("authenticated"):
            reply = "I need you to log in before I can look up orders."
        else:
            last = re.search(r"(latest|last|recent|status|track|where)", message.lower())
            ords = TOOL_REGISTRY["get_user_orders"](db, user, limit=5).get("orders", [])
            if not ords:
                reply = "You have no orders yet. Add something to the cart and check out — I'll track it here."
            else:
                o = ords[0]
                reply = (f"Your latest order **{o['order_number']}** (₹{o['total']:,.0f}) is **{o['status']}**"
                         + (f", tracking `{o.get('tracking_number','')}`." if o.get("tracking_number") else ".")
                         + (f" You have {len(ords)} recent orders; ask for a specific order number for details." if len(ords) > 1 else ""))
    elif intent == "compare":
        res = discover_products(db, user, kw, cat_hit, brand_hit, None, None, "popular", 4)
        cands = res.get("products", [])
        if len(cands) >= 2:
            comp = TOOL_REGISTRY["compare_products"](db, user, [c["id"] for c in cands[:3]])["comparison"]
            lines = [f"- **{c['name']}** — ₹{c['price']:,.0f}, ★{c['rating_avg']} ({c['rating_count']} reviews), stock {c['stock']}" for c in comp]
            best = min(comp, key=lambda c: c["price"])
            reply = "Here's a data-backed comparison:\n" + "\n".join(lines) + f"\n\nCheapest is **{best['name']}**; highest rated is **{max(comp, key=lambda c: c['rating_avg'])['name']}**."
            products = cands[:3]
        elif len(cands) == 1:
            reply = f"I found one match (**{cands[0]['name']}**). Give me another product name to compare it with."
            products = cands
        else:
            reply = "I couldn't find two matching products. Name the exact products (e.g. 'Compare Sony WH-1000XM6 vs Bose QC45')."
    elif intent == "offers":
        offers = TOOL_REGISTRY["get_current_offers"](db, user)
        lines = [f"`{c['code']}` — {c['description']}" for c in offers.get("coupons", [])[:4]]
        reply = "Current offers:\n" + ("\n".join(f"- {l}" for l in lines) if lines else "- No coupons right now.") + "\nPlus these discounted picks:"
        products = offers.get("deals", [])[:6]
    elif intent == "stock":
        res = discover_products(db, user, kw, cat_hit, brand_hit, None, None, "popular", 3)
        if res.get("products"):
            p = res["products"][0]
            inv = TOOL_REGISTRY["get_product_inventory"](db, user, p["id"])
            reply = f"**{p['name']}** has **{inv['total_available']}** units available."
            products = [p]
        else:
            low = db.query(models.Inventory).filter(
                models.Inventory.quantity <= models.Inventory.low_stock_threshold).limit(5).all()
            reply = "Low-stock alerts right now: " + (", ".join(
                (db.get(models.Product, r.product_id).name if db.get(models.Product, r.product_id) else "?")
                for r in low) if low else "nothing critical.")
    elif intent == "reviews":
        # "reviews of X" -> lookup; rating-constrained searches ("above 4.5",
        # "highest rating") -> discovery sorted by rating
        t = message.lower()
        wants_lookup = bool(re.search(r"reviews?\s+(of|for|about|on)\b", t))
        wants_discovery = bool(re.search(
            r"\b(which|highest|best|top|find|under|below|budget|above|over)\b", t)) and not wants_lookup
        if wants_discovery:
            sort = "rating" if re.search(r"\b(rating|rated|stars|best|top|highest)\b", message.lower()) else "popular"
            res = discover_products(db, user, kw, cat_hit, brand_hit, hi, rating_min, sort, 6)
            cands = res.get("products", [])
            if cands:
                reply = f"Top matches in the live catalog:\n" + "\n".join(
                    f"- **{p['name']}** — ₹{p['price']:,.0f} ★{p['rating_avg']}" for p in cands[:6])
                products = cands
            else:
                recs = TOOL_REGISTRY["get_recommendations"](db, user, limit=6).get("products", [])
                reply = "Nothing matched those exact filters. Here are highly-rated alternatives instead:" if recs else "Nothing matched those filters. Try broadening the budget or category."
                products = recs
            return reply, products
        res = discover_products(db, user, kw, cat_hit, brand_hit, None, None, "popular", 3)
        if res.get("products"):
            p = res["products"][0]
            revs = TOOL_REGISTRY["get_product_reviews"](db, user, p["id"], 3).get("reviews", [])
            if revs:
                reply = f"Top reviews for **{p['name']}** (★{p['rating_avg']}):\n" + "\n".join(
                    f"- ★{r['rating']} **{r['title']}** — {r['body'][:140]}" for r in revs)
            else:
                reply = f"**{p['name']}** has no reviews yet — be the first after purchase."
            products = [p]
        else:
            reply = "Tell me which product's reviews you want and I'll pull them."
    else:  # discover
        sort = "rating" if rating_min or "best" in message.lower() or "top" in message.lower() else "popular"
        res = discover_products(db, user, kw, cat_hit, brand_hit, hi, rating_min, sort, 6)
        cands = res.get("products", [])
        history = [{"role": m.role, "content": m.content} for m in
                   db.query(models.AgentMessage).filter_by(conversation_id=conv.id).order_by(
                       models.AgentMessage.created_at.desc()).limit(8).all()]
        catalog_ctx = "\n".join(f"- {p['name']} | ₹{p['price']:,.0f} | ★{p['rating_avg']}" for p in cands)
        llm = try_adk_reply(message, catalog_ctx, history)
        if cands:
            filt = f" under ₹{hi:,.0f}" if hi else ""
            why = "They match your budget and have the strongest ratings." if hi or rating_min else "These are the strongest matches in the live catalog."
            head = (llm + "\n\n" if llm else f"I found {res['total']} option(s){filt}, {greeting.strip() or 'friend'} — top picks:\n{why}")
            bullets = "\n".join(f"- **{p['name']}** — ₹{p['price']:,.0f} ★{p['rating_avg']}" for p in cands[:6])
            reply = head + ("\n" + bullets if not llm else "\n\n" + bullets)
            products = cands
        else:
            recs = TOOL_REGISTRY["get_recommendations"](db, user, limit=6).get("products", [])
            reply = (llm + "\n\n" if llm else "Nothing matched those exact filters. ") + \
                ("Here are highly-rated alternatives instead:" if recs else "Try broadening the budget or category.")
            products = recs

    reply = reply[:4000]
    return reply, products
