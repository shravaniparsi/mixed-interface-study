import pytest
import requests
import uuid
import time
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_author(name: Optional[str] = None, bio: Optional[str] = None, born_year: Optional[int] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Author")
    payload = {"name": name}
    if bio is not None:
        payload["bio"] = bio
    if born_year is not None:
        payload["born_year"] = born_year
    response = requests.post(f"{BASE_URL}/authors", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_category(name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = unique("Category")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = requests.post(f"{BASE_URL}/categories", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def create_book(title: Optional[str] = None, isbn: Optional[str] = None, price: float = 19.99,
                published_year: int = 2020, stock: int = 10, author_id: Optional[int] = None,
                category_id: Optional[int] = None) -> Dict[str, Any]:
    if title is None:
        title = unique("Book")
    if isbn is None:
        isbn = f"978{uuid.uuid4().hex[:10]}"
    if author_id is None:
        author = create_author()
        author_id = author["id"]
    if category_id is None:
        category = create_category()
        category_id = category["id"]
    payload = {
        "title": title,
        "isbn": isbn,
        "price": price,
        "published_year": published_year,
        "stock": stock,
        "author_id": author_id,
        "category_id": category_id
    }
    response = requests.post(f"{BASE_URL}/books", json=payload, timeout=TIMEOUT)
    assert response.status_code in (200, 201), f"Helper failed {response.status_code}: {response.text[:200]}"
    return response.json()

def test_health_check_returns_200():
    response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert response.status_code == 200

def test_create_author_with_valid_data():
    name = unique("Author")
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == name

def test_create_author_missing_required_field():
    response = requests.post(f"{BASE_URL}/authors", json={}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_create_author_invalid_name_length():
    name = "a" * 101
    response = requests.post(f"{BASE_URL}/authors", json={"name": name}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(error["loc"] == ["body", "name"] for error in data["detail"])

def test_list_authors_with_default_pagination():
    response = requests.get(f"{BASE_URL}/authors", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_list_authors_with_custom_pagination():
    response = requests.get(f"{BASE_URL}/authors", params={"skip": 0, "limit": 5}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

def test_get_existing_author():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author["id"]
    assert data["name"] == author["name"]

def test_get_nonexistent_author():
    response = requests.get(f"{BASE_URL}/authors/999999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_get_author_with_etag_not_modified():
    author = create_author()
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    etag = response.headers.get("ETag")
    assert etag is not None
    response = requests.get(f"{BASE_URL}/authors/{author['id']}", headers={"If-None-Match": etag}, timeout=TIMEOUT)
    assert response.status_code == 304

def test_update_author_with_valid_data():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

def test_update_author_with_etag_mismatch():
    author = create_author()
    new_name = unique("UpdatedAuthor")
    response = requests.put(f"{BASE_URL}/authors/{author['id']}", json={"name": new_name},
                           headers={"If-Match": "invalid-etag"}, timeout=TIMEOUT)
    assert response.status_code == 412

def test_delete_existing_author():
    author = create_author()
    response = requests.delete(f"{BASE_URL}/authors/{author['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

def test_create_book_with_valid_data():
    book = create_book()
    assert "id" in book
    assert "title" in book
    assert "isbn" in book

def test_create_book_missing_required_field():
    response = requests.post(f"{BASE_URL}/books", json={"title": "MissingFields"}, timeout=TIMEOUT)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_list_books_with_default_pagination():
    response = requests.get(f"{BASE_URL}/books", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data

def test_list_books_with_filters():
    author = create_author()
    category = create_category()
    book1 = create_book(author_id=author["id"], category_id=category["id"], price=10.0)
    book2 = create_book(author_id=author["id"], category_id=category["id"], price=20.0)

    response = requests.get(f"{BASE_URL}/books", params={
        "author_id": author["id"],
        "category_id": category["id"],
        "min_price": 5.0,
        "max_price": 15.0
    }, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == book1["id"]

def test_get_existing_book():
    book = create_book()
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]
    assert data["title"] == book["title"]

def test_get_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.get(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_get_nonexistent_book():
    response = requests.get(f"{BASE_URL}/books/999999", timeout=TIMEOUT)
    assert response.status_code == 404

def test_update_book_with_valid_data():
    book = create_book()
    new_title = unique("UpdatedBook")
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title

def test_update_book_with_etag_mismatch():
    book = create_book()
    new_title = unique("UpdatedBook")
    response = requests.put(f"{BASE_URL}/books/{book['id']}", json={"title": new_title},
                           headers={"If-Match": "invalid-etag"}, timeout=TIMEOUT)
    assert response.status_code == 412

def test_soft_delete_existing_book():
    book = create_book()
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 204

def test_delete_already_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    assert response.status_code == 410

def test_restore_soft_deleted_book():
    book = create_book()
    requests.delete(f"{BASE_URL}/books/{book['id']}", timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book["id"]

def test_restore_non_deleted_book():
    book = create_book()
    response = requests.post(f"{BASE_URL}/books/{book['id']}/restore", timeout=TIMEOUT)
    assert response.status_code == 400

def test_apply_valid_discount():
    book = create_book(price=100.0)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                            json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["discounted_price"] == 90.0

def test_apply_discount_exceeding_rate_limit():
    book = create_book(price=100.0)
    for _ in range(5):
        requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                     json={"discount_percent": 10.0}, timeout=TIMEOUT)
    response = requests.post(f"{BASE_URL}/books/{book['id']}/discount",
                            json={"discount_percent": 10.0}, timeout=TIMEOUT)
    assert response.status_code == 429

def test_upload_valid_cover_image():
    book = create_book()
    with open("test_cover.jpg", "wb") as f:
        f.write(b"dummy image data")
    with open("test_cover.jpg", "rb") as f:
        files = {"file": ("test_cover.jpg", f, "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == book["id"]
    assert data["filename"] == "test_cover.jpg"

def test_upload_oversized_cover_image():
    book = create_book()
    large_data = b"x" * (2 * 1024 * 1024 + 1)
    with open("large_cover.jpg", "wb") as f:
        f.write(large_data)
    with open("large_cover.jpg", "rb") as f:
        files = {"file": ("large_cover.jpg", f, "image/jpeg")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 413

def test_upload_invalid_file_type():
    book = create_book()
    with open("invalid_cover.txt", "wb") as f:
        f.write(b"not an image")
    with open("invalid_cover.txt", "rb") as f:
        files = {"file": ("invalid_cover.txt", f, "text/plain")}
        response = requests.post(f"{BASE_URL}/books/{book['id']}/cover", files=files, timeout=TIMEOUT)
    assert response.status_code == 415