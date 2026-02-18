"""
Reddit scraper using public JSON endpoints.
No OAuth/PRAW required. Uses https://www.reddit.com/r/{sub}/top.json
Rate limit: ~10 req/min → 6-9s delay between requests.
Output: data/posts.jsonl (one JSON object per line)
"""

import json
import os
import random
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "posts.jsonl"

MIN_SCORE = 5
MIN_BODY_CHARS = 50
REQUEST_DELAY = (6, 9)

SUBREDDITS = {
    # First sub in each sector is the probe target — must be text-heavy (self-posts)
    "tech": [
        "cscareerquestions",  # text-heavy: career Q&A
        "programming",        # mix of text + links
        "homelab",            # text-heavy: project posts
        "buildapc",           # text-heavy: advice requests
        "technology",         # mostly links — lower yield
        "apple", "Android", "gadgets",
    ],
    "financial": [
        "personalfinance",        # text-heavy: advice requests
        "povertyfinance",         # text-heavy
        "financialindependence",  # text-heavy: FIRE discussion
        "fatFIRE",
        "Bogleheads",
        "Frugal",
        "investing",
        "wallstreetbets",
    ],
    "political": [
        "NeutralPolitics",     # text-heavy: evidence-based posts
        "moderatepolitics",    # text-heavy: discussion
        "AskTrumpsupporters",  # text-heavy: Q&A
        "conservative",
        "progressive",
        "Libertarian",
        "centrist",
        "politics",            # mostly links — lower yield
    ],
}

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session


def fetch_json(url: str, session: requests.Session, attempt: int = 0) -> dict | None:
    try:
        resp = session.get(url, timeout=15)
    except requests.RequestException as exc:
        print(f"  [net error] {exc}")
        if attempt < 3:
            time.sleep(2 ** attempt)
            return fetch_json(url, session, attempt + 1)
        return None

    if resp.status_code == 429:
        wait = int(resp.headers.get("Retry-After", 60))
        print(f"  [429] rate limited — waiting {wait}s")
        time.sleep(wait)
        return fetch_json(url, session, attempt)

    if resp.status_code in (403, 404):
        print(f"  [{resp.status_code}] skipping — subreddit unavailable")
        return None

    if resp.status_code >= 500:
        if attempt < 4:
            backoff = 2 ** attempt
            print(f"  [{resp.status_code}] server error — retrying in {backoff}s")
            time.sleep(backoff)
            return fetch_json(url, session, attempt + 1)
        return None

    if resp.status_code != 200:
        print(f"  [unexpected {resp.status_code}] {url}")
        return None

    try:
        return resp.json()
    except json.JSONDecodeError:
        print("  [parse error] bad JSON response")
        return None


def iter_subreddit(
    subreddit: str,
    sector: str,
    session: requests.Session,
    sort: str = "top",
    time_filter: str = "year",
    max_pages: int = 5,
):
    after = None
    for page in range(max_pages):
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit=100&t={time_filter}"
        if after:
            url += f"&after={after}"

        print(f"  [{subreddit}] page {page + 1}/{max_pages} — {url}")
        data = fetch_json(url, session)

        if data is None:
            break

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        for child in children:
            post = child.get("data", {})
            if not post:
                continue

            score = post.get("score", 0) or 0
            body = (post.get("selftext") or "").strip()

            if score < MIN_SCORE:
                continue
            if body in ("", "[deleted]", "[removed]"):
                continue
            if len(body) < MIN_BODY_CHARS:
                continue

            author = post.get("author", "[deleted]")
            if author in ("[deleted]", "AutoModerator"):
                continue

            yield {
                "id": post["id"],
                "sector": sector,
                "subreddit": subreddit,
                "title": post.get("title", "").strip(),
                "selftext": body,
                "author": author,
                "score": score,
                "num_comments": post.get("num_comments", 0),
                "created_utc": post.get("created_utc"),
                "permalink": post.get("permalink", ""),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }

        after = data.get("data", {}).get("after")
        if not after:
            break

        delay = random.uniform(*REQUEST_DELAY)
        print(f"  sleeping {delay:.1f}s")
        time.sleep(delay)

        if page % 3 == 2:
            session.headers.update({"User-Agent": random.choice(USER_AGENTS)})


def _try_get_db_conn():
    """Return a DB connection if Postgres is reachable, else None."""
    try:
        from src.db import get_conn
        conn = get_conn()
        return conn
    except Exception:
        pass
    try:
        # Allow running from project root without package install
        sys.path.insert(0, str(Path(__file__).parent))
        from db import get_conn  # type: ignore
        conn = get_conn()
        return conn
    except Exception as exc:
        print(f"  [db] not available ({exc}) — JSONL only")
        return None


def run(
    sectors: list[str] | None = None,
    max_pages_per_sub: int = 2,
    probe: bool = False,
):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    targets = {k: v for k, v in SUBREDDITS.items() if sectors is None or k in sectors}
    session = make_session()
    total = 0
    db_total = 0
    seen_ids: set[str] = set()

    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for line in f:
                try:
                    seen_ids.add(json.loads(line)["id"])
                except (json.JSONDecodeError, KeyError):
                    pass
        print(f"Loaded {len(seen_ids)} existing post IDs from JSONL")

    conn = _try_get_db_conn()
    if conn:
        print("DB connection OK — will write to Postgres + JSONL")
    else:
        print("No DB — writing to JSONL only")

    try:
        from db import insert_posts  # type: ignore
    except ImportError:
        insert_posts = None

    with open(OUTPUT_FILE, "a") as out:
        for sector, subs in targets.items():
            if probe:
                subs = subs[:1]
            for sub in subs:
                print(f"\n=== {sector.upper()} / r/{sub} ===")
                batch = []
                for post in iter_subreddit(sub, sector, session, max_pages=max_pages_per_sub):
                    if post["id"] in seen_ids:
                        continue
                    seen_ids.add(post["id"])
                    out.write(json.dumps(post) + "\n")
                    batch.append(post)
                    total += 1
                    if total % 50 == 0:
                        out.flush()
                        print(f"  → {total} posts written so far")

                if conn and insert_posts and batch:
                    try:
                        n = insert_posts(conn, batch)
                        db_total += n
                        print(f"  → {n} rows inserted into DB ({db_total} total)")
                    except Exception as exc:
                        print(f"  [db insert error] {exc}")

                delay = random.uniform(*REQUEST_DELAY)
                print(f"  switching subreddit — sleeping {delay:.1f}s")
                time.sleep(delay)

    if conn:
        conn.close()

    print(f"\nDone. {total} new posts to JSONL, {db_total} to Postgres.")
    return total


if __name__ == "__main__":
    probe_mode = len(sys.argv) > 1 and sys.argv[1] == "probe"
    if probe_mode:
        print("PROBE MODE: 1 subreddit per sector, 1 page each")
        run(max_pages_per_sub=1, probe=True)
    else:
        run(max_pages_per_sub=2)
