import pytest
import pandas as pd
from src import MovieStorage
import main

def test_movies_persist(client, test_storage, uploaded_movies):
    # TODO: create another MovieStorage pointing to test_storage.db_path.
    # Use that object to get the movies and count them.
    # Check 20 rows, all four DataFrame columns, and the original title order.
    # Compare IDs from that object's select_columns() with GET /movies?limit=100.
    # Both should return IDs 1 through 20 in row order.
    MovieStorage2 = MovieStorage(test_storage.db_path)
    df = MovieStorage2.get()
    assert len(df) == 20
    assert MovieStorage2.count_movies() == 20
    assert list(df.columns) == ["title", "release_year", "rating", "genre"]
    
    original_df = pd.read_csv("fixtures/sample_movies.csv")
    original_titles = list(original_df["title"])
    saved_titles = list(df["title"])
    assert saved_titles == original_titles
    
    records = MovieStorage2.select_columns(["title"], limit=100)
    storage_ids = []
    for record in records:
        storage_ids.append(record["id"])
    
    response = client.get("/movies?limit=100")
    assert response.status_code == 200
    api_ids = []
    for record in response.json()["data"]:
        api_ids.append(record["id"])

    expected_ids = list(range(1, 21))
    assert storage_ids == expected_ids
    assert api_ids == expected_ids

def test_cache_and_processing(client, uploaded_movies, processing_body):
    # TODO 1: GET /movies with limits 100 and 1.
    # Check 200 and that main.cache.get(limit) equals each response body.

    # TODO 2: repeat limit=100 and check the same response.

    # TODO 3: POST /movies/process using json=processing_body.
    # Check 200, zero validation removals, and the 20 -> 16 cleaning report.
    # Confirm both old cache entries are None.

    # TODO 4: retrieve again; check total_rows=16 and titles Movie A through Movie P, in order.
    # Check IDs 1 through 16 in the retrieved records.
    # Check that the new response is cached.
    response_100 = client.get("/movies?limit=100")
    assert response_100.status_code == 200
    assert main.cache.get(100) == response_100.json()

    response_1 = client.get("/movies?limit=1")
    assert response_1.status_code == 200
    assert main.cache.get(1) == response_1.json()
    
    repeat_response = client.get("/movies?limit=100")
    assert repeat_response.status_code == 200
    assert repeat_response.json() == response_100.json()
   
    process_res = client.post("/movies/process", json=processing_body)
    assert process_res.status_code == 200

    process_data = process_res.json()
    assert process_data["validation_rows_removed"] == 0
    
    report = process_data["cleaning_report"]
    assert report["rows_before"] == 20
    assert report["rows_after"] == 16
    assert report["rows_removed"] == 4
    assert report["columns_before"] == 4
    assert report["columns_after"] == 4
    assert report["columns_removed"] == 0
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    new_response = client.get("/movies?limit=100")
    assert new_response.status_code == 200

    new_data = new_response.json()
    assert new_data["total_rows"] == 16

    expected_titles = []
    for letter in "ABCDEFGHIJKLMNOP":
        expected_titles.append("Movie " + letter)

    titles = []
    ids = []
    for record in new_data["data"]:
        titles.append(record["title"])
        ids.append(record["id"])

    assert titles == expected_titles
    assert ids == list(range(1, 17))
    assert main.cache.get(100) == new_data


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    # TODO 1: GET /movies with limit=100 to populate the cache.
    # Assert 200 and keep the response for comparison.

    # TODO 2: Use monkeypatch to replace main.storage.select_columns()
    # and main.storage.count_movies() with a function that fails the test
    # if either method is called. 

    # TODO 3: Repeat the same GET request.
    # Assert 200 and the same response body as the first request.
    first_response = client.get("/movies?limit=100")
    assert first_response.status_code == 200
    first_data = first_response.json()

    def fail_if_called(*args, **kwargs):
        pytest.fail("The database was used instead of the cache")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)
    second_response = client.get("/movies?limit=100")
    assert second_response.status_code == 200
    assert second_response.json() == first_data

