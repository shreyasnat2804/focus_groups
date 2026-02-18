# Stages to POC

This document outlines the sequential stages to reach a working Proof of Concept that can be demoed to potential clients. After the first client, development becomes dynamic and driven by customer needs.

---

## Stage 0: Data Discovery & Validation

**Goal:** Understand what data exists before building product features

**What to Build:**
- HTTP scraper using Reddit's public JSON endpoints (10 req/min, no auth required)
- Demographic tagging pipeline (3 layers: self-disclosure, subreddit mapping, NLP classifier)
- Postgres schema for storing tagged posts
- Basic analysis scripts

**Important Note on Reddit API:**
As of November 2025, Reddit eliminated self-service API access. OAuth credentials now require manual approval through the Responsible Builder Policy, with low approval rates for commercial/personal projects. Instead, we use Reddit's public JSON endpoints (append `.json` to any Reddit URL) which require no credentials and provide read-only access to all public content. Rate limit: ~10 requests/minute.

**Deliverables:**
- 50-100K tagged Reddit posts across major subreddits (collected over 1-2 weeks using public endpoints)
- Demographic distribution analysis (age, income, gender, political lean, geography)
- Sector richness assessment (tech, financial, political)
- Gap analysis: what demographics are under/over-represented
- Bubble identification: echo chambers and subcultures in the data

**Success Criteria:**
- Know exactly which demographics you can serve well
- Identify product positioning based on data strengths
- Understand Reddit's inherent biases
- Have a commercialization strategy based on actual coverage

**What NOT to Build Yet:**
- Vector embeddings
- Sector models / LoRA fine-tuning
- Web UI
- Focus group orchestration
- Claude API integration

---

## Stage 1: Data Pipeline & Infrastructure

**Goal:** Production-grade data collection and storage

**What to Build:**
- Continuous scraper using JSON endpoints running on Lambda CPU instance
- Automated demographic tagging on ingestion
- Cloud SQL (Postgres + pgvector) on GCP
- Data quality checks and monitoring
- Backup and recovery processes

**Scraper Implementation:**
Uses Reddit's public JSON endpoints (no OAuth required). Implements strict 10 req/min rate limiting with exponential backoff on 429 errors. Rotates user agents and adds randomized delays to avoid detection. Handles pagination for subreddits with >100 posts.

**Deliverables:**
- Scraper runs 24/7 with automatic recovery
- Database grows continuously with fresh data
- Demographic tags applied in real-time
- Monitoring dashboard showing data health
- 500K+ tagged posts across all sectors

**Success Criteria:**
- Pipeline runs unsupervised for 7+ days without failures
- Data quality metrics above threshold (>80% tagged posts)
- Cost under budget (<$100/month)
- Can pause/resume scraping without data loss

---

## Stage 2: Persona Engine

**Goal:** Transform tagged posts into queryable personas

**What to Build:**
- Embedding generation pipeline (sentence-transformers)
- pgvector storage and indexing
- Persona selection algorithms (diversity, representativeness)
- Persona quality scoring

**Deliverables:**
- All posts have vector embeddings
- Fast persona queries (<100ms for 50 personas)
- Diversity algorithm ensures varied perspectives
- Persona "cards" with demographic + behavioral traits

**Success Criteria:**
- Can select 50 diverse personas matching criteria in <1 second
- Personas demonstrably different from each other (embedding distance)
- Manual review shows personas feel authentic
- Coverage across all major demographic segments

---

## Stage 3: MVP Focus Group Product

**Goal:** Ship a working product that customers can use

**What to Build:**
- FastAPI backend on Cloud Run
- React frontend on Cloud Run
- Session management (create, run, view results)
- Claude API integration for generating persona responses
- Basic reporting (qualitative responses per persona)

**Deliverables:**
- Web UI for creating focus groups
- Users can specify persona criteria and questions
- System returns responses from 20-50 AI personas
- Export results as PDF/CSV
- Basic authentication and user accounts

**Success Criteria:**
- Complete focus group session in <5 minutes
- Responses feel authentic and varied
- 5-10 beta customers using the product
- Product runs without manual intervention
- Positive qualitative feedback from users

---

## POC Complete → First Client

At this point you have:
- Working product that runs unsupervised
- Demonstrable results (focus group sessions with 20-50 personas)
- Clear value proposition backed by real data
- 5-10 beta users providing feedback
- Known costs and unit economics

**What happens after first client:**
Development becomes customer-driven and dynamic. Priorities will be determined by:
- Customer feedback and feature requests
- Revenue opportunities
- Competitive pressures
- Technical debt that needs addressing

**Possible next directions:**
- Advanced analytics (sentiment, divergence, bubble detection)
- Sector-specific fine-tuned models
- Enterprise features (SSO, audit logs, compliance)
- API access for customers
- White-label options
- Multi-turn AI moderation

The roadmap past POC is intentionally unplanned — let the market tell you what to build.

