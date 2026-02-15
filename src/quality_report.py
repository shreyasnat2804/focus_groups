import json
import sqlite3
from collections import Counter
from pathlib import Path

from src.database import DB_PATH, get_connection, get_post_count


def generate_report(db_path=None):
    conn = get_connection(db_path)
    total = get_post_count(db_path)

    if total == 0:
        print("No posts in database.")
        return

    print(f"=== Data Quality Report ===\n")
    print(f"Total posts: {total}\n")

    # Posts per subreddit
    rows = conn.execute("SELECT subreddit, COUNT(*) as cnt FROM posts GROUP BY subreddit ORDER BY cnt DESC").fetchall()
    print("Posts per subreddit:")
    for sub, cnt in rows:
        print(f"  r/{sub}: {cnt}")

    # Demographic breakdowns
    all_tags = conn.execute("SELECT demographic_tags FROM posts").fetchall()
    age_counts = Counter()
    gender_counts = Counter()
    income_counts = Counter()
    confidences = []

    for (tags_json,) in all_tags:
        tags = json.loads(tags_json) if tags_json else {}
        age_counts[tags.get("age_group", "unknown")] += 1
        gender_counts[tags.get("gender", "unknown")] += 1
        income_counts[tags.get("income_proxy", "unknown")] += 1
        if "confidence" in tags:
            confidences.append(tags["confidence"])

    print(f"\nAge groups:")
    for k, v in age_counts.most_common():
        print(f"  {k}: {v} ({v/total*100:.1f}%)")

    print(f"\nGender:")
    for k, v in gender_counts.most_common():
        print(f"  {k}: {v} ({v/total*100:.1f}%)")

    print(f"\nIncome proxy:")
    for k, v in income_counts.most_common():
        print(f"  {k}: {v} ({v/total*100:.1f}%)")

    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        print(f"\nAvg demographic confidence: {avg_conf:.2f}")

    # Temporal distribution
    rows = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM posts WHERE timestamp > 0").fetchone()
    if rows[0]:
        from datetime import datetime
        min_dt = datetime.utcfromtimestamp(rows[0]).strftime("%Y-%m-%d")
        max_dt = datetime.utcfromtimestamp(rows[1]).strftime("%Y-%m-%d")
        print(f"\nTemporal range: {min_dt} to {max_dt}")

    conn.close()

    # Save markdown report
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    md_path = reports_dir / "data_quality.md"

    conn2 = get_connection(db_path)
    sub_rows = conn2.execute("SELECT subreddit, COUNT(*) as cnt FROM posts GROUP BY subreddit ORDER BY cnt DESC").fetchall()
    conn2.close()

    with open(md_path, "w") as f:
        f.write(f"# Data Quality Report\n\nTotal posts: {total}\n\n")
        f.write("## Posts per Subreddit\n\n")
        for sub, cnt in sub_rows:
            f.write(f"- r/{sub}: {cnt}\n")
        f.write(f"\n## Age Groups\n\n")
        for k, v in age_counts.most_common():
            f.write(f"- {k}: {v} ({v/total*100:.1f}%)\n")
        f.write(f"\n## Gender\n\n")
        for k, v in gender_counts.most_common():
            f.write(f"- {k}: {v} ({v/total*100:.1f}%)\n")
        f.write(f"\n## Income Proxy\n\n")
        for k, v in income_counts.most_common():
            f.write(f"- {k}: {v} ({v/total*100:.1f}%)\n")
        if confidences:
            f.write(f"\nAvg demographic confidence: {sum(confidences)/len(confidences):.2f}\n")

    print(f"\nReport saved to {md_path}")


def main():
    generate_report()


if __name__ == "__main__":
    main()
