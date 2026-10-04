# Nova — AI-Powered E-Commerce Platform

A **production-grade, full-stack e-commerce application** with a deeply integrated
**Google ADK (Gemini) AI shopping agent** that operates on real backend data —
not mocks.

- **Frontend:** Next.js 16 · TypeScript · Tailwind CSS v4 · TanStack Query · Zustand ·
  React Hook Form + Zod · Lucide icons · dark/light theme
- **Backend:** FastAPI · Pydantic v2 · SQLAlchemy 2 · PostgreSQL (SQLite for local dev) ·
  Alembic · JWT (access + refresh) · RBAC
- **AI agent:** Google ADK / Gemini (`google-genai`) with 25+ service-backed tools,
  conversation memory, SSE streaming, product-aware chat UI — plus a deterministic
  local planner fallback so everything works without an API key.

## Folder structure

```text
.
├── src/                      # frontend (Next.js, this directory)
│   ├── app/                  # routes: /, products, search, cart, checkout,
│   │                         # orders, wishlist, profile, login/register, admin/*
│   ├── components/           # Header/Footer, ProductCard, ChatWidget, ui, admin
│   ├── lib/                  # typed API client (JWT refresh, SSE), formatting
│   ├── stores/               # zustand: auth, ui
│   └── types/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint, CORS, rate limiting, errors
│   │   ├── config.py         # env-driven settings (no secrets in code)
│   │   ├── models.py         # 26 relational tables, UUID PKs, indexes
│   │   ├── api/v1/           # auth, products, categories, brands, search,
│   │   │                     # cart, wishlist, orders, reviews, coupons,
│   │   │                     # inventory, admin, analytics, agent
│   │   ├── services/         # business logic (single source of truth)
│   │   ├── agents/           # root_agent + 25+ tools (service-backed)
│   │   └── seed/seed.py      # deterministic large dataset generator
│   ├── migrations/           # Alembic (initial schema included, verified)
│   └── tests/
├── docker-compose.yml        # postgres + backend + frontend
├── .env.example
└── Makefile
```

## Environment setup

```bash
cp .env.example .env          # then fill GOOGLE_API_KEY to enable Gemini
# frontend local default (already created): .env.local
#   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL (sqlite local, postgres in prod) | `sqlite:///./ecommerce.db` |
| `SECRET_KEY` / `REFRESH_SECRET_KEY` | JWT signing | dev-only placeholder |
| `CORS_ORIGINS` | allowed origins | `http://localhost:3000` |
| `GOOGLE_API_KEY` | enables Gemini enhancement of agent replies | empty → local planner |
| `GOOGLE_GENAI_MODEL` / `AGENT_MODEL` | Gemini model | `gemini-2.0-flash` |
| `DEMO_PASSWORD` | seed password for demo accounts | `password123` |
| `NEXT_PUBLIC_API_URL` | frontend → backend base URL | `http://localhost:8000/api/v1` |

## Database setup / migrations / seed

```bash
cd backend
pip install -r requirements.txt

# fresh DB via Alembic (postgres or sqlite):
DATABASE_URL="postgresql://nova:nova@localhost:5432/nova" python -m alembic upgrade head

# deterministic large seed (131 categories, 63 brands, 1200 products,
# 2400+ variants, 5000+ reviews, 1000+ users, 600+ orders, coupons).
# Products carry real product-relevant photography (per-model image sets) and
# authentic colourway/edition names — no lorem text or random placeholder art.
python -m app.seed.seed --products 1200 --users 1000
```

Local dev uses SQLite + `Base.metadata.create_all` on startup; Postgres is used
via `DATABASE_URL` (docker-compose sets it automatically).

Demo accounts (password `password123` or `$DEMO_PASSWORD`):

- `customer@example.com` — customer with cart, wishlist, 2 tracked orders
- `admin@example.com` — admin for `/admin`
- `manager1@example.com` — manager role

## Running

```bash
# backend (from backend/)
uvicorn app.main:app --reload --port 8000   # docs: http://localhost:8000/docs

# frontend (from repo root)
pnpm install && pnpm dev                    # http://localhost:3000

# everything (needs Docker)
docker compose up --build
```

## Google ADK setup

1. Get a Gemini API key and set `GOOGLE_API_KEY` in `.env`.
2. The agent (`backend/app/agents/`) wraps the live catalog: `try_adk_reply()`
   calls `google.genai` with the system prompt + live tool results as context.
3. Without a key, the deterministic planner uses the **same tools**, so all
   agent behavior (search, compare, cart actions, order tracking) keeps working.

### Agent architecture

```text
Root Shopping Agent  (SYSTEM_PROMPT in agents/root_agent.py)
├── Product Discovery  search/filter/recommend/compare/reviews/stock
├── Shopping Assistant cart/wishlist/offers/coupons
├── Order Assistant    orders/tracking
└── Customer Assistant profile/support + conversation memory
```

Tools (`agents/tools.py`, 25 total) call **service-layer functions only** —
the model never touches SQL, credentials, or tokens (guardrails + rate limits
in `main.py`).

## API documentation

Interactive docs: `http://localhost:8000/docs` and `/redoc`.
Key routes (prefix `/api/v1`): `/auth`, `/users`, `/products`, `/categories`,
`/brands`, `/search?q=&category=&brand=&min_price=&max_price=&rating=&sort=`,
`/cart`, `/wishlist`, `/orders/checkout`, `/reviews`, `/coupons`,
`/inventory`, `/admin`, `/analytics`, `/agent/chat` (+ `/agent/chat/stream`
SSE, `/agent/conversations`).

**Guest shopping:** add-to-cart works without an account — items persist in
`localStorage` with backend-identical totals (free shipping ≥ ₹999, 18% tax)
and merge into the server cart automatically on login/signup (including agent
"add to cart" requests).

Errors use the envelope `{"error": {"code": "...", "message": "..."}}`
with proper 400/401/403/404/409/422/429/500 handling.

## Testing

```bash
cd backend && python -m pytest tests -q     # auth, products, search, cart,
                                            # orders, coupons, agent tools
```

Agent acceptance questions (all answered from live DB data, verified):

- "Show me laptops under ₹80,000" · "Which phone has the highest rating?"
- "Find headphones under ₹10,000 with rating above 4.5"
- "Compare Sony headphones and Bose headphones" · "Add … to my cart"
- "What is my latest order?" · "Show me my wishlist" · "Current discounts?"

## Production deployment

- Set real `SECRET_KEY`s, `DATABASE_URL` (Postgres), `CORS_ORIGINS`, `GOOGLE_API_KEY`.
- Run `alembic upgrade head`, then seed once.
- Serve backend with uvicorn/gunicorn behind TLS; `pnpm build && pnpm start`
  for the frontend (or deploy it on Vercel with `NEXT_PUBLIC_API_URL` set).
- Never commit `.env`, `*.db`, or credentials — `.gitignore` covers them.
