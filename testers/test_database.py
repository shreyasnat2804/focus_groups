import os
import tempfile
from src.database import init_db, insert_posts, get_post_count, get_scrape_progress, update_scrape_progress


def test_init_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        init_db(path)
        assert os.path.exists(path)
        assert get_post_count(path) == 0
    finally:
        os.unlink(path)


def test_insert_and_count():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        init_db(path)
        posts = [
            {"post_id": "1", "text": "hello", "subreddit": "test", "demographic_tags": {}, "timestamp": 100, "source": "reddit", "scrape_date": "2024-01-01"},
            {"post_id": "2", "text": "world", "subreddit": "test", "demographic_tags": {"age_group": "18-24"}, "timestamp": 200, "source": "reddit", "scrape_date": "2024-01-01"},
        ]
        insert_posts(posts, path)
        assert get_post_count(path) == 2

        # Duplicates ignored
        insert_posts(posts, path)
        assert get_post_count(path) == 2
    finally:
        os.unlink(path)


def test_scrape_progress():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        init_db(path)
        progress = get_scrape_progress("testsub", path)
        assert progress["last_post_id"] is None
        assert progress["posts_scraped"] == 0

        update_scrape_progress("testsub", "abc123", 50, path)
        progress = get_scrape_progress("testsub", path)
        assert progress["last_post_id"] == "abc123"
        assert progress["posts_scraped"] == 50
    finally:
        os.unlink(path)
