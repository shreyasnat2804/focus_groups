"""Quick DB health check — run from project root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from db import get_conn

try:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        print("Postgres:", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM posts;")
        print("posts table row count:", cur.fetchone()[0])
    conn.close()
    print("DB OK")
except Exception as e:
    print(f"DB ERROR: {e}")
    sys.exit(1)
