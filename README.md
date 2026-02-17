# Synthetic Focus Groups

AI-powered platform that simulates focus group responses using demographic-conditioned sector models. Fine-tunes LoRA adapters on Mistral-7B for tech, financial, and political sectors.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Reddit API credentials (create at https://www.reddit.com/prefs/apps)

### Setup

```bash
# Clone and enter
git clone <repo_url> && cd focus_groups

# Environment
cp .env.example .env
# Edit .env with your Reddit API credentials and Postgres password

# Start local Postgres + pgvector
docker-compose up -d

# Python deps
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Verify DB
psql -h localhost -U fg_user -d focusgroups -c "SELECT 1;"
```

### Project Structure

```
├── CLAUDE.md              # AI assistant context + state
├── skills/                # Detailed reference docs per subsystem
├── src/                   # Application code
├── tests/                 # Test suite
├── db/                    # SQL migrations and init scripts
├── docker-compose.yml     # Local Postgres + pgvector
└── requirements.txt       # Python dependencies
```

## Architecture

```
Reddit → Scraper → Postgres (raw posts)
  → Demographic Tagger → tagged posts
  → sentence-transformers → pgvector embeddings
  → LoRA fine-tune (per sector) → Mistral-7B adapters
  → FastAPI API → React frontend
```

See `skills/` directory for detailed docs on each component.
