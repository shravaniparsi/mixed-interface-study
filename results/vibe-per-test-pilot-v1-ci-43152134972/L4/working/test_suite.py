import uuid
import time
import requests
from typing import Optional

BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"
AUTH = {"X-API-Key": API_KEY}

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def reset_db():
    r = requests.post(f"{BASE_URL}/reset")
    assert r.status_code == 200

def create_author(name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = 1980):
    name = name or unique("Author")
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": name, "bio": bio, "born_year": born_year,
    })
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_category(name: Optional[str] = None):
    name = name or unique("Category")
    r = requests.post(f"{BASE_URL}/categories", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_book(author_id: int, category_id: int, title: Optional[str] = None,
                isbn: Optional[str] = None, price: float = 29.99, published_year: int = 2020, stock: int = 10):
    title = title or unique("Book")
    isbn = isbn or unique("ISBN")[:13]
    r = requests.post(f"{BASE_URL}/books", json={
        "title": title, "isbn": isbn, "price": price,
        "published_year": published_year, "stock": stock,
        "author_id": author_id, "category_id": category_id,
    })
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_tag(name: Optional[str] = None):
    name = name or unique("Tag")
    r = requests.post(f"{BASE_URL}/tags", json={"name": name})
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def create_order(customer_name: Optional[str] = None, customer_email: Optional[str] = None, items: Optional[list] = None):
    customer_name = customer_name or unique("Customer")
    customer_email = customer_email or f"{uuid.uuid4().hex[:8]}@test.com"
    items = items or []
    r = requests.post(f"{BASE_URL}/orders", json={
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
    })
    assert r.status_code in (200, 201), f"Helper failed {r.status_code}: {r.text[:200]}"
    return r.json()

def setup_book_with_deps(isbn: Optional[str] = None, stock: int = 10, price: float = 29.99,
                         published_year: int = 2020, author_name: Optional[str] = None, cat_name: Optional[str] = None):
    a = create_author(name=author_name or unique("Author"))
    c = create_category(name=cat_name or unique("Category"))
    b = create_book(a["id"], c["id"], isbn=isbn or unique("ISBN")[:13], stock=stock,
                    price=price, published_year=published_year)
    return a, c, b

def test_create_author_happy_path():
    data = create_author(name=unique("George Orwell"), born_year=1903)
    assert data["name"].startswith("George Orwell")
    assert data["born_year"] == 1903
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_create_author_missing_required_field():
    r = requests.post(f"{BASE_URL}/authors", json={"bio": "no name"})
    assert r.status_code == 422
    assert "detail" in r.json()
    assert any(error["loc"] == ["body", "name"] for error in r.json()["detail"])

def test_create_author_invalid_born_year():
    r = requests.post(f"{BASE_URL}/authors", json={
        "name": unique("Author"),
        "born_year": 2027
    })
    assert r.status_code == 422
    assert "detail" in r.json()
    assert any(error["loc"] == ["body", "born_year"] for error in r.json()["detail"])

def test_list_authors_happy_path():
    create_author(name=unique("Author1"))
    create_author(name=unique("Author2"))
    r = requests.get(f"{BASE_URL}/authors")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 2

def test_list_authors_with_skip_and_limit():
    create_author(name=unique("AuthorSkip1"))
    create_author(name=unique("AuthorSkip2"))
    create_author(name=unique("AuthorSkip3"))
    r = requests.get(f"{BASE_URL}/authors", params={"skip": 1, "limit": 1})
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_get_author_happy_path():
    author = create_author(name=unique("TestAuthor"))
    r = requests.get(f"{BASE_URL}/authors/{author['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == author["id"]
    assert r.json()["name"] == author["name"]

def test_get_nonexistent_author():
    r = requests.get(f"{BASE_URL}/authors/999999")
    assert r.status_code == 404
    assert "detail" in r.json()

def test_get_author_with_etag_not_modified():
    author = create_author(name=unique("ETagAuthor"))
    r = requests.get(f"{BASE_URL}/authors/{author['id']}")
    assert r.status_code == 200
    etag = r.headers.get("ETag")
    assert etag is not None

    r2 = requests.get(f"{BASE_URL}/authors/{author['id']}",
                     headers={"If-None-Match": etag})
    assert r2.status_code == 304

def test_update_author_happy_path():
    author = create_author(name=unique("OldName"))
    r = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "NewName"})
    assert r.status_code == 200
    assert r.json()["name"] == "NewName"
    assert r.json()["id"] == author["id"]

def test_update_author_with_etag_mismatch():
    author = create_author(name=unique("ETagAuthor"))
    r1 = requests.get(f"{BASE_URL}/authors/{author['id']}")
    old_etag = r1.headers["ETag"]

    requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": "ChangedName"})

    r2 = requests.put(f"{BASE_URL}/authors/{author['id']}",
                     json={"name": "StaleUpdate"},
                     headers={"If-Match": old_etag})
    assert r2.status_code == 412
    assert "detail" in r2.json()

def test_delete_author_with_books_fails():
    a, c, b = setup_book_with_deps(isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/authors/{a['id']}")
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_happy_path():
    a = create_author(name=unique("BookAuthor"))
    c = create_category(name=unique("BookCategory"))
    book = create_book(a["id"], c["id"], title=unique("TestBook"))
    assert book["title"].startswith("TestBook")
    assert "id" in book
    assert book["author_id"] == a["id"]
    assert book["category_id"] == c["id"]

def test_create_book_duplicate_isbn():
    isbn = unique("ISBN")[:13]
    a, c, _ = setup_book_with_deps(isbn=isbn)
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Dup", "isbn": isbn, "price": 10,
        "published_year": 2020, "stock": 5,
        "author_id": a["id"], "category_id": c["id"],
    })
    assert r.status_code == 409
    assert "detail" in r.json()

def test_create_book_invalid_price():
    a = create_author(name=unique("PriceAuthor"))
    c = create_category(name=unique("PriceCategory"))
    r = requests.post(f"{BASE_URL}/books", json={
        "title": "Cheap", "isbn": unique("ISBN")[:13], "price": -5,
        "published_year": 2020, "author_id": a["id"], "category_id": c["id"],
    })
    assert r.status_code == 422
    assert "detail" in r.json()
    assert any(error["loc"] == ["body", "price"] for error in r.json()["detail"])

def test_list_books_happy_path():
    a, c, b = setup_book_with_deps(isbn=unique("ISBN")[:13])
    r = requests.get(f"{BASE_URL}/books")
    assert r.status_code == 200
    assert "items" in r.json()
    assert isinstance(r.json()["items"], list)
    assert len(r.json()["items"]) >= 1

def test_list_books_with_filters():
    a1 = create_author(name=unique("FilterAuthor1"))
    a2 = create_author(name=unique("FilterAuthor2"))
    c1 = create_category(name=unique("FilterCategory1"))
    c2 = create_category(name=unique("FilterCategory2"))

    b1 = create_book(a1["id"], c1["id"], isbn=unique("ISBN")[:13], price=10.0)
    b2 = create_book(a2["id"], c2["id"], isbn=unique("ISBN")[:13], price=20.0)

    r = requests.get(f"{BASE_URL}/books", params={
        "author_id": a1["id"],
        "min_price": 5,
        "max_price": 15
    })
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    assert r.json()["items"][0]["id"] == b1["id"]

def test_get_book_happy_path():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13])
    r = requests.get(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]
    assert "author" in r.json()
    assert "category" in r.json()

def test_get_soft_deleted_book():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 204

    r = requests.get(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 410
    assert "detail" in r.json()

def test_update_book_happy_path():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13])
    r = requests.put(f"{BASE_URL}/books/{book['id']}", json={
        "title": "Updated Title",
        "price": 39.99
    })
    assert r.status_code == 200
    assert r.json()["title"] == "Updated Title"
    assert r.json()["price"] == 39.99

def test_soft_delete_book_happy_path():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 204

    r = requests.get(f"{BASE_URL}/books")
    assert r.status_code == 200
    assert all(item["id"] != book["id"] for item in r.json()["items"])

def test_restore_book_happy_path():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13])
    r = requests.delete(f"{BASE_URL}/books/{book['id']}")
    assert r.status_code == 204

    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == book["id"]
    assert r.json()["is_deleted"] is False

    r = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=30)
    assert r.status_code == 200
    assert r.json()["is_deleted"] is False

def test_restore_non_deleted_book():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/restore")
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_happy_path():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13], price=100, published_year=2020)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                     json={"discount_percent": 25})
    assert r.status_code == 200
    assert r.json()["discounted_price"] == 75.0
    assert r.json()["book_id"] == book["id"]

def test_apply_discount_to_new_book():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13], price=50, published_year=2026)
    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                     json={"discount_percent": 10})
    assert r.status_code == 400
    assert "detail" in r.json()

def test_apply_discount_rate_limit_exceeded():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13], published_year=2020, price=100)
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                         json={"discount_percent": 10})
        assert r.status_code == 200

    r = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                     json={"discount_percent": 10})
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert "detail" in r.json()

def test_update_stock_happy_path():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13], stock=5)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": 10})
    assert r.status_code == 200
    assert r.json()["stock"] == 15

def test_update_stock_insufficient():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13], stock=3)
    r = requests.patch(f"{BASE_URL}/books/{book['id']}/stock", params={"quantity": -10})
    assert r.status_code == 400
    assert "detail" in r.json()
    assert "Insufficient stock" in r.json()["detail"]

def test_create_review_happy_path():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13])
    r = requests.post(f"{BASE_URL}/books/{book['id']}/reviews",
                     json={"rating": 5, "reviewer_name": "Alice"})
    assert r.status_code == 201
    assert r.json()["book_id"] == book["id"]
    assert r.json()["rating"] == 5
    assert r.json()["reviewer_name"] == "Alice"

def test_list_reviews_happy_path():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews",
                 json={"rating": 5, "reviewer_name": "Alice"})
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews",
                 json={"rating": 3, "reviewer_name": "Bob"})

    r = requests.get(f"{BASE_URL}/books/{book['id']}/reviews")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) == 2

def test_get_book_rating_happy_path():
    _, _, book = setup_book_with_deps(isbn=unique("ISBN")[:13])
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews",
                 json={"rating": 5, "reviewer_name": "Alice"})
    requests.post(f"{BASE_URL}/books/{book['id']}/reviews",
                 json={"rating": 3, "reviewer_name": "Bob"})

    r = requests.get(f"{BASE_URL}/books/{book['id']}/rating")
    assert r.status_code == 200
    assert r.json()["average_rating"] == 4.0
    assert r.json()["review_count"] == 2