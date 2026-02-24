"""Quick summary of what's in the DB."""
from focus_groups.db import get_conn

conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM posts;")
    print(f"Total posts: {cur.fetchone()[0]}")

    cur.execute("""
        SELECT metadata->>'sector' AS sector, subreddit, COUNT(*) AS n
        FROM posts
        GROUP BY sector, subreddit
        ORDER BY sector, n DESC;
    """)
    print(f"\n{'Sector':<12} {'Subreddit':<25} {'Posts':>5}")
    print("-" * 45)
    for row in cur.fetchall():
        print(f"{row[0]:<12} {row[1]:<25} {row[2]:>5}")
conn.close()
