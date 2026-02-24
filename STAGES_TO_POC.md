# Stages to POC

POC goal: a working RAG + Claude demo that simulates focus groups. This validates the concept before investing in LoRA-tuned sector models (the real product).

---

## Stage 0: Data Discovery & Validation  [DONE]

**Goal:** Understand what data exists before building anything.

**What was built:**
- HTTP scraper using Reddit's public JSON endpoints (10 req/min, no auth)
- 3-layer demographic tagging pipeline (self-disclosure, subreddit priors, NLP)
- Postgres schema for tagged posts

---

## Stage 1: Data Pipeline & Infrastructure  [DONE]

**Goal:** Validate the pipeline with real data locally.

**What was built:**
- Local scraper (30K posts across financial, tech, political sectors)
- Automated demographic tagging on ingestion
- Local Postgres + pgvector (Docker)
- Data quality checks and CSV export

---

## Stage 2: Persona Engine  [DONE]

**Goal:** Turn tagged posts into queryable, diverse personas via embeddings.

**What was built:**
- `sentence-transformers` embeddings (all-MiniLM-L6-v2, 384 dims) for all 24K posts
- pgvector storage + ivfflat index
- MMR-based persona selection (filter by demographics/sector, diversify via embedding distance)
- `personas/` library with clean imports for Stage 3
- `build_system_prompt()` to format PersonaCards into Claude system prompts

**Current state:** 23,933 posts embedded, 97 tests passing, persona selection <1s.

---

## Stage 3: RAG + Claude POC  [NEXT]

**Goal:** Ship a demo that runs a synthetic focus group using Claude as the generation layer. This proves the concept before building LoRA sector models.

**Architecture:**
```
User question + persona criteria
        |
  select_personas() — retrieves N diverse posts from pgvector
        |
  build_system_prompt() — formats each persona as a Claude system prompt
        |
  Claude API — generates a response in each persona's voice
        |
  Collected responses = simulated focus group
```

**What to build:**
- FastAPI backend (Cloud Run) — session creation, persona selection, Claude calls
- React frontend (Cloud Run) — specify criteria, ask questions, view responses
- Claude API integration — one call per persona, system prompt from `personas.profiles`
- Session storage — save focus group results for review
- Export — PDF/CSV of session results

**What this is NOT:**
- Not the final product. Claude is a stand-in for what will eventually be LoRA-tuned sector models (Mistral-7B).
- Not optimized for cost. Claude API calls at 20-50 personas per session will be expensive at scale. The LoRA models solve this.
- Not fine-tuned. Responses rely entirely on the system prompt + retrieved post context. Quality will improve significantly with sector-specific fine-tuning.

**Success criteria:**
- Complete a focus group session in <5 minutes
- Responses feel authentic and varied across personas
- Demonstrable to potential clients
- Runs without manual intervention

---

## After POC: LoRA Sector Models (the real product)

The POC proves the concept with Claude. The production product replaces Claude with self-hosted LoRA fine-tuned models:

- **3 sector models** (tech, financial, political) fine-tuned on Mistral-7B
- **Self-hosted inference** — eliminates per-call Claude API costs
- **Better persona fidelity** — models trained on actual sector discourse, not prompted
- **Lambda GPU** for training, Cloud Run or dedicated GPU for inference

This happens after POC validates demand with real clients.
