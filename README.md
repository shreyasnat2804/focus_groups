# FocusTest

AI-powered synthetic focus group platform. Pitch a product, get real sentiment feedback from diverse, demographically-accurate personas sourced from Reddit data — plus pricing analysis using proven econometric methods.

<video src="my-video/out/FocusTestDemo.mp4" controls width="100%"></video>

## How It Works

```
Reddit (PRAW) → 23k+ tagged posts → sentence-transformers embeddings → pgvector
    ↓
Demographic Tagger (3-layer: self-disclosure, subreddit priors, NLP)
    ↓
MMR Persona Selection (demographic filters + diversity)
    ↓
Claude API (system prompt per persona) → Focus Group Responses
    ↓
Van Westendorp PSM + Gabor-Granger → Pricing Recommendations
```

## Features

- **Synthetic Focus Groups** — Create sessions with custom questions, demographic filters, and sector targeting. Auto-select N diverse personas and generate responses via Claude API with persona-specific system prompts.
- **Pricing Analysis (WTP)** — Van Westendorp Price Sensitivity Meter and Gabor-Granger demand curves across one-time, subscription, and hybrid pricing models.
- **Market Segmentation** — Break down pricing by income bracket, age group, gender, or sector.
- **Export** — PDF and CSV export of full session results.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11+) |
| Frontend | React 19, Vite, Recharts |
| Database | Postgres 16 + pgvector |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Generation | Anthropic Claude API |
| Scraping | PRAW |
| Deploy | GCP Cloud Run, Cloud SQL, Cloud Storage |

## Setup

**Prerequisites:** Python 3.11+, Node.js 18+, Docker

```bash
# Clone & configure
git clone <repo-url>
cd focus_groups
cp .env.example .env  # Set ANTHROPIC_API_KEY

# Python environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Database
docker-compose up -d

# Backend
uvicorn focus_groups.api:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Testing

```bash
python3 -m pytest tests/ -v
```

## Project Structure

```
src/focus_groups/
├── api.py              # FastAPI routes
├── claude.py           # Anthropic API integration
├── sessions.py         # Session CRUD
├── personas/
│   ├── selection.py    # MMR persona selection
│   ├── profiles.py     # System prompt generation
│   └── mmr.py          # MMR algorithm
├── wtp/                # Pricing analysis
│   ├── van_westendorp.py
│   ├── gabor_granger.py
│   ├── segmentation.py
│   └── prompts/        # WTP prompt templates
├── embeddings.py       # sentence-transformers
├── tagger.py           # Demographic inference
└── export.py           # PDF/CSV export

frontend/src/
├── pages/
│   ├── NewPitch.jsx    # Create session
│   ├── PitchResults.jsx # Results + pricing
│   └── PitchList.jsx   # Home
└── components/
    ├── PricingAnalysis.jsx
    ├── VanWestendorpChart.jsx
    └── DemandCurveChart.jsx
```
