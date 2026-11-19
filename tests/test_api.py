import asyncio, sys, pytest, pytest_asyncio
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from utils.settings import settings
from api.main import app, limiter
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import api.main as api_main


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

TEST_DB_NAME = "book_crawler_pytest"

@pytest_asyncio.fixture
async def seeded_test_db(monkeypatch):
    # Safety guard: never allow destructive test cleanup
    # against a non-test database.
    assert "test" in TEST_DB_NAME.lower() or "pytest" in TEST_DB_NAME.lower()

    test_client = AsyncIOMotorClient(settings.MONGO_URI)
    test_db = test_client[TEST_DB_NAME]

    # Start every test from a known state
    await test_db.books.delete_many({})
    await test_db.changes.delete_many({})

    books = [
        {
            "_id": ObjectId(),
            "title": "Poetry Book",
            "category": "Poetry",
            "price_incl": 15.0,
            "rating": 2,
            "num_reviews": 10,
            "crawled_at": datetime(2026, 1, 1),
        },
        {
            "_id": ObjectId(),
            "title": "Science Book",
            "category": "Science",
            "price_incl": 45.0,
            "rating": 5,
            "num_reviews": 25,
            "crawled_at": datetime(2026, 1, 2),
        },
        {
            "_id": ObjectId(),
            "title": "History Book",
            "category": "History",
            "price_incl": 80.0,
            "rating": 3,
            "num_reviews": 5,
            "crawled_at": datetime(2026, 1, 3),
        },
    ]

    await test_db.books.insert_many(books)
    await test_db.changes.insert_one(
        {
            "book_id": books[0]["_id"],
            "type": 1,
            "updated_at": datetime(2026, 1, 4),
            "data": {},
        }
    )

    # Make the FastAPI endpoints use the test DB
    monkeypatch.setattr(api_main, "db", test_db)

    yield {
        "db": test_db,
        "books": books,
    }

    # Cleanup only the dedicated test DB
    await test_db.books.delete_many({})
    await test_db.changes.delete_many({})

    test_client.close()

@pytest_asyncio.fixture
async def client(seeded_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
def valid_headers():
    return {"API-KEY": settings.API_KEY}


@pytest.mark.asyncio
async def test_get_books_no_auth(client):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/books")
        assert resp.status_code == 401
        assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_get_books_with_auth(client, valid_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/books", headers=valid_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "books" in data
        assert isinstance(data["books"], list)
        assert "total_count" in data
        assert "page" in data


@pytest.mark.asyncio
async def test_filter_books_by_category(client, valid_headers):
    resp = await client.get("/books", headers=valid_headers, params={"category": "Poetry"})
    print("--------------------Response--------------------")
    print(resp)
    assert resp.status_code == 200
    data = resp.json()
    assert all("Poetry" in b["category"] for b in data["books"])


@pytest.mark.asyncio
async def test_filter_books_by_price_range(client, valid_headers):
    resp = await client.get(
        "/books", headers=valid_headers, params={"min_price": 10, "max_price": 50}
    )
    assert resp.status_code == 200
    data = resp.json()
    for book in data["books"]:
        assert 10 <= book["price_incl"] <= 50


@pytest.mark.asyncio
async def test_sort_books_by_rating(client, valid_headers):
    resp = await client.get("/books", headers=valid_headers, params={"sort_by": "rating"})
    assert resp.status_code == 200
    data = resp.json()
    ratings = [b["rating"] for b in data["books"]]
    assert ratings == sorted(ratings)

@pytest.mark.asyncio
async def test_get_book_by_id(client, valid_headers, seeded_test_db):

    known_book = seeded_test_db["books"][0]
    book_id = str(known_book["_id"])

    detail_resp = await client.get(f"/books/{book_id}", headers=valid_headers)
    assert detail_resp.status_code == 200

    data = detail_resp.json()
    assert data["_id"] == book_id
    assert data["title"] == "Poetry Book"
    assert data["category"] == "Poetry"
    assert data["price_incl"] == 15.0
    assert data["rating"] == 2


@pytest.mark.asyncio
async def test_get_changes(client, valid_headers):
    resp = await client.get("/changes", headers=valid_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "total_count" in data
    assert "page" in data
    assert "changes" in data
    assert isinstance(data["changes"], list)
    
    if data["changes"]:
        first_change = data["changes"][0]
        assert "type" in first_change
        assert "book_id" in first_change


@pytest.mark.asyncio
async def test_rate_limiting(client, valid_headers, reset_rate_limiter):
    for _ in range(100):
        resp = await client.get("/books", headers=valid_headers)
        assert resp.status_code == 200

    resp = await client.get("/books", headers=valid_headers)
    assert resp.status_code == 429

@pytest.fixture
def reset_rate_limiter():
    limiter.reset()

    yield

    limiter.reset()
