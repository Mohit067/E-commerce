"""Smoke tests: auth, products, search, cart, orders, coupons, agent tools."""
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def _signup(email="t1@example.com"):
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": "password123", "full_name": "T"})
    assert r.status_code in (200, 409), r.text
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_health():
    assert client.get("/health").status_code == 200


def test_products_and_search():
    r = client.get("/api/v1/products?page=1&page_size=5")
    assert r.status_code == 200
    assert "items" in r.json()
    r = client.get("/api/v1/search?q=laptop")
    assert r.status_code == 200
    assert "suggestions" in r.json()


def test_cart_orders_agent_flow():
    token = _signup("flow@example.com")
    h = {"Authorization": f"Bearer {token}"}
    prods = client.get("/api/v1/products?page=1&page_size=3").json()["items"]
    assert prods, "seed some products first"
    pid = prods[0]["id"]
    r = client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 1}, headers=h)
    assert r.status_code == 200, r.text
    r = client.get("/api/v1/cart", headers=h)
    assert r.json()["total"] >= 0
    r = client.post("/api/v1/orders/checkout", json={"payment_provider": "mock"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("confirmed", "pending")
    r = client.post("/api/v1/agent/chat", json={"message": "Show me laptops under 80000"})
    assert r.status_code == 200
    assert r.json()["reply"]
    # agent action questions from the spec
    for q in ["Which phone has the highest rating?",
              "What are the current discounts?",
              "Show products from Nike."]:
        r = client.post("/api/v1/agent/chat", json={"message": q})
        assert r.status_code == 200, q
        assert r.json()["reply"]
