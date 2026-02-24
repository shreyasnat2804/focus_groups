"""
Reddit scraper using public JSON endpoints.
No OAuth/PRAW required. Uses https://www.reddit.com/r/{sub}/new.json
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

DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "posts.jsonl"

MIN_SCORE = 5
MIN_BODY_CHARS = 50
REQUEST_DELAY = (6, 9)

# Region codes for subreddits with a clear geographic audience.
# Subreddits not listed here are treated as US/global (region=None).
SUBREDDIT_REGIONS: dict[str, str] = {
    # UK
    "UKPersonalFinance": "UK",
    "ukpolitics":        "UK",
    "unitedkingdom":     "UK",
    # Australia
    "AusFinance":          "AU",
    "AustralianPolitics":  "AU",
    "australia":           "AU",
    # Canada
    "CanadianInvestor": "CA",
    "PersonalFinanceCanada": "CA",
    "CanadaPolitics":   "CA",
    # India
    "personalfinanceindia": "IN",
    "IndiaInvestments":     "IN",
    # Europe
    "eupersonalfinance": "EU",
    "europe":            "EU",
}

SUBREDDITS = {
    # First sub in each sector is the probe target — must be text-heavy (self-posts)
    "tech": [
        "cscareerquestions",  # text-heavy: career Q&A
        "programming",        # mix of text + links
        "homelab",            # text-heavy: project posts
        "buildapc",           # text-heavy: advice requests
        "techsupport",        # text-heavy: help requests
        "apple", "Android", "AskTechnology",
        "learnprogramming",   # text-heavy: beginner Q&A
        "webdev",             # text-heavy: dev discussions
        "devops",             # text-heavy: ops discussions
        "sysadmin",           # text-heavy: IT discussions
        "MachineLearning",    # research + discussion
        "datascience",        # text-heavy: career + methods
        "ExperiencedDevs",    # text-heavy: senior eng discussions
        "cybersecurity",      # text-heavy: security Q&A
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
        "financialplanning",      # text-heavy: planning Q&A
        "realestateinvesting",    # text-heavy: RE discussion
        "UKPersonalFinance",      # text-heavy — region: UK
        "AusFinance",             # text-heavy — region: AU
        "CanadianInvestor",       # text-heavy — region: CA
        "PersonalFinanceCanada",  # text-heavy — region: CA
        "personalfinanceindia",   # text-heavy — region: IN
        "eupersonalfinance",      # text-heavy — region: EU
    ],
    "political": [
        "NeutralPolitics",      # text-heavy: evidence-based posts
        "moderatepolitics",     # text-heavy: discussion
        "AskTrumpsupporters",   # text-heavy: Q&A
        "Ask_Politics",         # text-heavy: Q&A format
        "PoliticalDiscussion",  # text-heavy: discussion
        "conservative",
        "Libertarian",
        "centrist",
        "AskALiberal",          # text-heavy: Q&A complement
        "ukpolitics",           # text-heavy — region: UK
        "AustralianPolitics",   # text-heavy — region: AU
        "CanadaPolitics",       # text-heavy — region: CA
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
    sort: str = "new",
    max_pages: int = 20,
    min_date: datetime | None = None,
):
    """
    Paginate through a subreddit and yield qualifying posts.

    sort="new" (default) paginates backwards in time — ideal for a date cutoff.
    min_date: stop paginating once any post on a page falls before this date.
              Posts before min_date on the final partial page are skipped.
    """
    min_date_ts = min_date.timestamp() if min_date else None
    after = None

    for page in range(max_pages):
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit=100"
        if after:
            url += f"&after={after}"

        print(f"  [{subreddit}] page {page + 1} — {url}")
        data = fetch_json(url, session)

        if data is None:
            break

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        hit_cutoff = False
        for child in children:
            post = child.get("data", {})
            if not post:
                continue

            # Date cutoff — skip this post; if any post is past cutoff, stop after page
            created_ts = post.get("created_utc", 0) or 0
            if min_date_ts and created_ts < min_date_ts:
                hit_cutoff = True
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
                "region": SUBREDDIT_REGIONS.get(subreddit),  # None = US/global
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

        if hit_cutoff:
            print(f"  [{subreddit}] reached date cutoff — stopping")
            break

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
        from focus_groups.db import get_conn
        conn = get_conn()
        return conn
    except Exception as exc:
        print(f"  [db] not available ({exc}) — JSONL only")
        return None


def run(
    sectors: list[str] | None = None,
    max_pages_per_sub: int = 20,
    probe: bool = False,
    min_date: datetime | None = datetime(2021, 1, 1, tzinfo=timezone.utc),
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
        from focus_groups.db import insert_posts, get_post_ids_by_source_ids, insert_tags
    except ImportError:
        insert_posts = None
        get_post_ids_by_source_ids = None
        insert_tags = None

    try:
        from focus_groups.tagger import tag_post
    except ImportError:
        tag_post = None

    with open(OUTPUT_FILE, "a") as out:
        for sector, subs in targets.items():
            if probe:
                subs = subs[:1]
            for sub in subs:
                print(f"\n=== {sector.upper()} / r/{sub} ===")
                batch = []
                for post in iter_subreddit(sub, sector, session, max_pages=max_pages_per_sub, min_date=min_date):
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
                        batch = []  # don't attempt tagging if insert failed

                if conn and get_post_ids_by_source_ids and insert_tags and tag_post and batch:
                    try:
                        id_map = get_post_ids_by_source_ids(conn, [p["id"] for p in batch])
                        tag_rows = []
                        for post in batch:
                            db_id = id_map.get(post["id"])
                            if db_id is None:
                                continue  # duplicate post, already tagged
                            text = f"{post.get('title', '')} {post.get('selftext', '')}"
                            for tag in tag_post(text, post["subreddit"]):
                                tag["post_id"] = db_id
                                tag_rows.append(tag)
                        if tag_rows:
                            n_tags = insert_tags(conn, tag_rows)
                            print(f"  → {n_tags} tags inserted")
                    except Exception as exc:
                        print(f"  [tagger error] {exc}")

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
        print("Scraping 2021–2026 posts across all sectors (target: 30k)")
        run()
