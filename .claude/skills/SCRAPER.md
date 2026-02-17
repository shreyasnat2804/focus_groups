# SCRAPER.md — Reddit Data Collection via PRAW

## PRAW Setup

```python
import praw

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="focusgroup-research/0.1 by /u/YOUR_USERNAME",
)
```

Store credentials in `.env` (never committed):
```
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
```

## Rate Limits

- **OAuth API**: 60 requests/minute (1 per second sustained)
- PRAW handles rate limiting internally but log when it throttles
- Each `.submissions()` call fetches up to 100 posts (one API call)
- Each `.comments()` call on a submission is 1 API call
- **Budget**: ~3,600 posts/hour from listing endpoints, more from Pushshift-style archives

## Subreddit Targets by Sector

### Tech
| Subreddit | Demographic Signal | Size |
|-----------|-------------------|------|
| r/technology | General tech consumers | 15M+ |
| r/gadgets | Product-focused consumers | 20M+ |
| r/apple, r/android | Platform-specific opinions | 5M+ each |
| r/programming | Developer perspective | 5M+ |
| r/sysadmin | Enterprise IT | 800k |

### Financial
| Subreddit | Demographic Signal | Size |
|-----------|-------------------|------|
| r/personalfinance | Broad income distribution | 18M+ |
| r/povertyfinance | Lower income | 1.5M |
| r/fatFIRE | High income | 500k |
| r/investing | Active investors | 2M+ |
| r/CreditCards | Consumer credit users | 300k |

### Political
| Subreddit | Demographic Signal | Size |
|-----------|-------------------|------|
| r/politics | Left-leaning general | 8M+ |
| r/conservative | Right-leaning | 1M+ |
| r/moderatepolitics | Centrist | 400k |
| r/neoliberal | Center-left policy | 200k |
| r/libertarian | Libertarian | 500k |

## Scraping Strategy

1. **Time range**: Posts from 2022-01-01 to 2024-06-30 (pre-prediction window)
2. **Sort**: Use `top` (time-filtered) and `hot` — skip `new` (too noisy)
3. **Minimum score**: 5+ upvotes to filter spam/low-effort
4. **Collect both posts and top-level comments** — comments often have richer demographic signals
5. **Store author bios** when available (user.subreddit.public_description) for demographic inference

## Scraping Pattern

```python
def scrape_subreddit(reddit, subreddit_name, limit=1000):
    sub = reddit.subreddit(subreddit_name)
    posts = []
    for submission in sub.top(time_filter="year", limit=limit):
        posts.append({
            "source_id": f"t3_{submission.id}",
            "subreddit": subreddit_name,
            "author": str(submission.author) if submission.author else "[deleted]",
            "text": f"{submission.title}\n\n{submission.selftext}" if submission.selftext else submission.title,
            "score": submission.score,
            "created_utc": datetime.utcfromtimestamp(submission.created_utc),
            "metadata": json.dumps({"flair": submission.link_flair_text, "num_comments": submission.num_comments}),
        })
    return posts
```

## Running on Lambda CPU

Lambda CPU instances are cheap for scraping (no GPU needed):
```bash
ssh user@lambda-cpu-instance
tmux new -s scraper
cd /home/user/focus_groups
python3 src/scraper.py --subreddits tech --limit 5000
```

Use `tmux` so the job survives SSH disconnects.

## Pitfalls

- **Deleted/suspended authors**: Check `submission.author is not None` before accessing profile
- **Rate limit 429s**: PRAW auto-retries but log these. If persistent, your credentials may be flagged
- **Pushshift is unreliable**: Don't depend on it. Use PRAW listing endpoints + time filtering
- **Reddit API changes**: Reddit restricted API access in 2023. OAuth with a script app still works for research but monitor for policy changes
- **Duplicate runs**: Always use `ON CONFLICT DO NOTHING` in DB inserts — re-running a scrape is expected
