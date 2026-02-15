import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "demographics_corpus.db"


def get_connection(db_path=None):
    return sqlite3.connect(db_path or DB_PATH)


def init_db(db_path=None):
    conn = get_connection(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            subreddit TEXT NOT NULL,
            demographic_tags JSON,
            timestamp INTEGER,
            source TEXT NOT NULL,
            scrape_date TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_progress (
            subreddit TEXT PRIMARY KEY,
            last_post_id TEXT,
            posts_scraped INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    return db_path or DB_PATH


def insert_posts(posts, db_path=None):
    """Insert posts, skipping duplicates. posts: list of dicts."""
    conn = get_connection(db_path)
    inserted = 0
    for p in posts:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO posts (post_id, text, subreddit, demographic_tags, timestamp, source, scrape_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["post_id"], p["text"], p["subreddit"], json.dumps(p["demographic_tags"]), p["timestamp"], p["source"], p["scrape_date"]),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return inserted


def get_post_count(db_path=None):
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    conn.close()
    return count


def get_demographic_summary(db_path=None):
    conn = get_connection(db_path)
    rows = conn.execute("SELECT demographic_tags, COUNT(*) FROM posts GROUP BY demographic_tags").fetchall()
    conn.close()
    summary = {}
    for tags_json, count in rows:
        tags = json.loads(tags_json) if tags_json else {}
        key = str(tags)
        summary[key] = count
    return summary


def get_scrape_progress(subreddit, db_path=None):
    conn = get_connection(db_path)
    row = conn.execute("SELECT last_post_id, posts_scraped FROM scrape_progress WHERE subreddit = ?", (subreddit,)).fetchone()
    conn.close()
    if row:
        return {"last_post_id": row[0], "posts_scraped": row[1]}
    return {"last_post_id": None, "posts_scraped": 0}


def update_scrape_progress(subreddit, last_post_id, posts_scraped, db_path=None):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO scrape_progress (subreddit, last_post_id, posts_scraped) VALUES (?, ?, ?)",
        (subreddit, last_post_id, posts_scraped),
    )
    conn.commit()
    conn.close()
