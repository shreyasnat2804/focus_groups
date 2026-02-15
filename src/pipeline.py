import argparse
import json
import time
from pathlib import Path

from src.database import get_post_count, init_db
from src.scraper import get_reddit, scrape_subreddit

CONFIG_PATH = Path(__file__).parent.parent / "config" / "subreddits.json"


def run(target=100000, config_path=None):
    config_path = config_path or CONFIG_PATH
    with open(config_path) as f:
        subreddits = json.load(f)

    print("Initializing database...")
    init_db()

    print(f"Target: {target} posts")
    print(f"Subreddits: {len(subreddits)}")

    reddit = get_reddit()
    total_new = 0
    start = time.time()

    for i, (sub_name, sub_config) in enumerate(subreddits.items(), 1):
        current_count = get_post_count()
        if current_count >= target:
            print(f"Reached target ({current_count}/{target}), stopping.")
            break

        limit = sub_config.get("post_limit", 5000)
        print(f"[{i}/{len(subreddits)}] Scraping r/{sub_name} (limit: {limit})...")

        new = scrape_subreddit(reddit, sub_name, post_limit=limit)
        total_new += new
        elapsed = time.time() - start
        print(f"  +{new} posts | Total: {get_post_count()} | Elapsed: {elapsed:.0f}s")

    final_count = get_post_count()
    print(f"\nDone. {total_new} new posts added. Total corpus: {final_count}")


def main():
    parser = argparse.ArgumentParser(description="Run the data collection pipeline")
    parser.add_argument("--target", type=int, default=100000, help="Target number of posts")
    parser.add_argument("--subreddits", type=str, default=None, help="Path to subreddits config JSON")
    args = parser.parse_args()
    run(target=args.target, config_path=args.subreddits)


if __name__ == "__main__":
    main()
