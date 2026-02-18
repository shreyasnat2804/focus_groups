# SCRAPER Skill

This skill covers Reddit data collection using public JSON endpoints.

---

## Critical Context: Reddit API Changes (November 2025)

Reddit eliminated self-service API access in November 2025. New OAuth credentials require manual approval through the Responsible Builder Policy, with very low approval rates for commercial/personal projects.

**Our approach:** Use Reddit's public JSON endpoints instead
- No credentials required
- Read-only access to all public content
- Rate limited to ~10 requests/minute
- 100% legal and compliant with Reddit's ToS for public data

**DO NOT use PRAW or attempt OAuth flow unless you have pre-existing credentials**

---

## Reddit JSON Endpoint Patterns

### Base URL Format
Append `.json` to any Reddit URL to get structured data:

```
Subreddit posts:
https://www.reddit.com/r/{subreddit}/{sort}.json?limit=100&after={pagination_token}

Sort options: hot, new, top, rising
Time filters (for top): hour, day, week, month, year, all

Specific post + comments:
https://www.reddit.com/r/{subreddit}/comments/{post_id}.json

User profile:
https://www.reddit.com/user/{username}.json
```

### Example Response Structure
```json
{
  "kind": "Listing",
  "data": {
    "after": "t3_abc123",
    "children": [
      {
        "kind": "t3",
        "data": {
          "id": "abc123",
          "title": "Post title",
          "selftext": "Post body text",
          "author": "username",
          "subreddit": "personalfinance",
          "created_utc": 1234567890,
          "score": 42,
          "num_comments": 15,
          "permalink": "/r/personalfinance/comments/abc123/..."
        }
      }
    ]
  }
}
```

---

## Rate Limiting (CRITICAL)

**Hard limit:** ~10 requests per minute for unauthenticated access
**Strategy:** 6-7 second delay between requests minimum

```python
import time
import random

def rate_limited_get(url, session):
    """Fetch with rate limiting"""
    response = session.get(url)
    
    # Handle rate limit errors
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after}s")
        time.sleep(retry_after)
        return rate_limited_get(url, session)
    
    # Add random delay to stay under limit
    delay = random.uniform(6, 8)
    time.sleep(delay)
    
    return response
```

**Important:** Reddit tracks by IP. If scraping from data center IPs (Lambda, GCP), you may face stricter limits or blocks. Consider:
- Running from residential IP initially
- Adding realistic user-agent headers
- Randomizing request timing
- Not hammering single subreddit repeatedly

---

## Scraper Architecture

### Phase 1: Local Development (Stage 0)
```
Python script on laptop
├── requests library for HTTP
├── SQLite for local testing
└── CSV export for analysis
```

### Phase 2: Production (Stage 1)
```
Lambda CPU instance (continuous)
├── Python 3.11
├── psycopg2 for Postgres writes
├── Cloud SQL connection
└── Systemd service or cron for scheduling
```

---

## Target Subreddits by Sector

### Financial Sector
```python
FINANCIAL_SUBREDDITS = [
    'personalfinance',      # General advice, middle income
    'povertyfinance',       # Low income focused
    'financialindependence',# FIRE movement, high income
    'fatFIRE',             # Very high income ($5M+ net worth)
    'Frugal',              # Budget-conscious
    'investing',           # Stock market discussion
    'wallstreetbets',      # Risk-tolerant traders
    'Bogleheads',          # Conservative investors
]
```

### Tech Sector
```python
TECH_SUBREDDITS = [
    'technology',          # General tech news
    'apple',              # Apple products
    'Android',            # Android ecosystem
    'gadgets',            # Consumer electronics
    'buildapc',           # PC building, budget-conscious
    'programming',        # Software developers
    'cscareerquestions',  # Tech workers
    'homelab',            # Tech enthusiasts
]
```

### Political Sector
```python
POLITICAL_SUBREDDITS = [
    'politics',           # Left-leaning general
    'conservative',       # Right-leaning
    'moderatepolitics',   # Center
    'NeutralPolitics',    # Evidence-based discussion
    'AskTrumpsupporters', # Conservative perspective
    'progressive',        # Left-wing
    'Libertarian',        # Libertarian
    'centrist',          # Moderate
]
```

### Demographic-Rich (for inference training)
```python
DEMOGRAPHIC_SUBREDDITS = [
    'teenagers',          # Age: <20
    'AskOldPeople',       # Age: 60+
    'TwoXChromosomes',    # Gender: Female
    'AskMen',            # Gender: Male
    'blackladies',       # Race + Gender
    'AsianAmerican',     # Ethnicity
]
```

---

## Data Schema (What to Scrape)

### Minimum Required Fields
```sql
CREATE TABLE reddit_posts (
    id VARCHAR(20) PRIMARY KEY,           -- Reddit post ID
    subreddit VARCHAR(50) NOT NULL,       -- Subreddit name
    title TEXT NOT NULL,                  -- Post title
    selftext TEXT,                        -- Post body (null for links)
    author VARCHAR(50),                   -- Username (can be [deleted])
    created_utc BIGINT NOT NULL,          -- Unix timestamp
    score INTEGER,                        -- Upvotes - downvotes
    num_comments INTEGER,                 -- Comment count
    permalink TEXT,                       -- Reddit URL path
    scraped_at TIMESTAMP DEFAULT NOW(),   -- When we collected it
    
    -- Indexes for common queries
    INDEX idx_subreddit (subreddit),
    INDEX idx_created (created_utc),
    INDEX idx_author (author)
);
```

### Optional Enrichment Fields
```sql
-- Add if needed for analysis
url TEXT,                    -- External link URL
is_self BOOLEAN,             -- Self-post vs link
link_flair_text VARCHAR(100),-- Post flair
over_18 BOOLEAN,             -- NSFW flag
```

---

## Scraping Strategy

### Stage 0: Historical Backfill
**Goal:** Collect diverse corpus quickly

```python
# For each subreddit
for subreddit in TARGET_SUBREDDITS:
    # Get top posts from last month
    fetch_posts(subreddit, sort='top', time='month', limit=1000)
    
    # Get recent posts
    fetch_posts(subreddit, sort='new', limit=500)
    
# Estimated time: 50 subreddits × 15 requests each ÷ 10 req/min = ~2 hours
```

### Stage 1: Continuous Monitoring
**Goal:** Stay current with fresh data

```python
# Every hour
for subreddit in TARGET_SUBREDDITS:
    fetch_posts(subreddit, sort='new', limit=25)  # Last hour's posts
    
# Estimated: 50 subreddits × 1 request ÷ 10 req/min = 5 minutes per hour
```

---

## Error Handling

### Common Issues

**429 Rate Limit**
```python
if response.status_code == 429:
    retry_after = int(response.headers.get('Retry-After', 60))
    time.sleep(retry_after)
    # Retry request
```

**403 Forbidden (IP blocked)**
```python
# Reddit detected scraping behavior
# Solutions:
# 1. Add realistic user-agent
# 2. Increase delays between requests
# 3. Switch to residential IP
# 4. Rotate IPs if using proxy service
```

**500/502/503 Server Errors**
```python
# Reddit is down, just retry with exponential backoff
time.sleep(2 ** attempt)  # 2s, 4s, 8s, 16s...
```

**Deleted/Private Subreddits**
```python
# Subreddit returns 403/404
# Log and skip, move to next
```

---

## Anti-Detection Best Practices

### User Agent
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}
```

### Request Timing
```python
# Don't use fixed delays - add randomness
delay = random.uniform(6, 9)  # Not exactly 7 seconds
time.sleep(delay)
```

### Pagination
```python
# Use Reddit's 'after' token for pagination
url = f'https://reddit.com/r/{subreddit}/new.json?limit=100&after={after_token}'
```

### Session Management
```python
import requests

# Reuse session for connection pooling
session = requests.Session()
session.headers.update({'User-Agent': '...'})
```

---

## Testing Checklist

Before deploying scraper:
- [ ] Rate limiting works (measure actual req/min)
- [ ] Pagination retrieves >100 posts correctly
- [ ] Error handling recovers from 429/500 errors
- [ ] Data writes to Postgres without duplicates
- [ ] Can run for 1+ hour without crashes
- [ ] Logs are readable and actionable

---

## Monitoring (Stage 1)

Track these metrics:
- Posts scraped per hour
- Errors per subreddit
- Rate limit hits
- Database write failures
- Scraper uptime

Alert on:
- Zero posts scraped for 2+ hours (scraper crashed)
- >50% error rate (Reddit blocking or API changes)
- Disk/memory usage spikes

---

## Cost Estimate

**Stage 0 (local):** $0
- Runs on your laptop
- ~2-3 days of intermittent scraping

**Stage 1 (Lambda):**
- CPU instance: $0.30/hr × 730hr/month = $220/month
- Network egress: ~$5/month
- **Total: ~$225/month**

**Optimization:** Run scraper only 6 hours/day = $55/month
