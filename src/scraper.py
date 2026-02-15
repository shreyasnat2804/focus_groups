import os
import time
from datetime import datetime

import praw
from dotenv import load_dotenv

from src.database import get_scrape_progress, insert_posts, update_scrape_progress
from src.demographics import tag_post

load_dotenv()

CUTOFF_TIMESTAMP = int(datetime(2024, 1, 1).timestamp())


def get_reddit():
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ.get("REDDIT_USER_AGENT", "focus_groups_scraper/0.1"),
    )


def scrape_subreddit(reddit, subreddit_name, post_limit=1000, include_comments=True, db_path=None):
    """Scrape submissions and top-level comments from a subreddit. Returns count of posts inserted."""
    progress = get_scrape_progress(subreddit_name, db_path)
    already_scraped = progress["posts_scraped"]
    if already_scraped >= post_limit:
        print(f"  r/{subreddit_name}: already at {already_scraped}/{post_limit}, skipping")
        return 0

    subreddit = reddit.subreddit(subreddit_name)
    batch = []
    last_id = None
    scraped = 0
    now = datetime.utcnow().isoformat()[:10]

    try:
        for submission in subreddit.top(time_filter="all", limit=None):
            if submission.created_utc >= CUTOFF_TIMESTAMP:
                continue
            if len(submission.selftext.strip()) < 20 and len(submission.title.strip()) < 20:
                continue

            text = f"{submission.title}\n{submission.selftext}".strip()
            tags = tag_post(text, subreddit_name)
            batch.append({
                "post_id": f"reddit_{submission.id}",
                "text": text[:5000],
                "subreddit": subreddit_name,
                "demographic_tags": tags,
                "timestamp": int(submission.created_utc),
                "source": "reddit",
                "scrape_date": now,
            })
            last_id = submission.id
            scraped += 1

            # Top-level comments
            if include_comments:
                submission.comments.replace_more(limit=0)
                for comment in submission.comments[:5]:
                    if comment.created_utc >= CUTOFF_TIMESTAMP:
                        continue
                    if len(comment.body.strip()) < 20:
                        continue
                    c_tags = tag_post(comment.body, subreddit_name)
                    batch.append({
                        "post_id": f"reddit_{comment.id}",
                        "text": comment.body[:5000],
                        "subreddit": subreddit_name,
                        "demographic_tags": c_tags,
                        "timestamp": int(comment.created_utc),
                        "source": "reddit",
                        "scrape_date": now,
                    })
                    scraped += 1

            # Batch insert every 100 posts
            if len(batch) >= 100:
                insert_posts(batch, db_path)
                batch = []

            if already_scraped + scraped >= post_limit:
                break

            # Rate limiting
            time.sleep(0.1)

    except Exception as e:
        print(f"  Error scraping r/{subreddit_name}: {e}")

    # Insert remaining
    if batch:
        insert_posts(batch, db_path)

    update_scrape_progress(subreddit_name, last_id, already_scraped + scraped, db_path)
    return scraped
