# CLAUDE.md

AI-powered synthetic focus group platform. Uses demographic-conditioned sector models (tech, financial, political) to simulate focus group responses.

## Skill Files

Detailed reference docs live in `.claude/skills/`. Load the relevant one for context:

| File | Covers |
|------|--------|
| `.claude/skills/DATABASE.md` | Postgres + pgvector schema, connection patterns |
| `.claude/skills/SCRAPER.md` | PRAW config, rate limits, subreddit targets |
| `.claude/skills/TAGGING.md` | 3-layer demographic inference pipeline |
| `.claude/skills/COMPUTE.md` | Lambda GPU/CPU instances, SSH, job management |
| `.claude/skills/CLOUD.md` | GCP project structure, Cloud SQL, Cloud Run, Storage |
| `.claude/skills/EMBEDDINGS.md` | sentence-transformers, pgvector write patterns |
| `.claude/skills/LORA.md` | Sector model architecture, LoRA training config |

## Tech Stack

- **Data**: Postgres 16 + pgvector (local Docker → Cloud SQL)
- **Scraping**: PRAW on Lambda CPU
- **Embeddings**: sentence-transformers on Lambda GPU / Colab
- **Fine-tuning**: LoRA on Mistral-7B (Lambda GPU)
- **Storage**: GCP Cloud Storage
- **Backend**: FastAPI on Cloud Run
- **Frontend**: React on Cloud Run

## Architecture

```
Reddit (PRAW) → Postgres (raw posts)
  → Demographic Tagger (3-layer) → tagged posts
  → sentence-transformers → pgvector embeddings
  → LoRA fine-tune (per sector) → sector models
  → FastAPI backend → React frontend
```

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-17 | Postgres + pgvector over SQLite | Need vector similarity search + concurrent access for API |
| 2026-02-17 | Mistral-7B base over Llama 3.1 8B | Better instruction following at similar size, permissive license |
| 2026-02-17 | 3 sector models over 1 general model | Domain-specific fine-tuning yields better predictions per sector |
| 2026-02-17 | Lambda GPU over Colab for training | Persistent SSH, no session timeouts, better for LoRA jobs |

## Git Workflow

- Commit regularly and logically — each commit should represent one coherent codebase change (e.g. "add tests for X", "implement X module", "update imports for X"). Don't batch unrelated changes into one commit, and don't wait until the end of a prompt to commit everything at once.
- Push to remote at the end of every prompt, after all commits are made
- Use `git revert` if something breaks — no force-push or history rewriting
- Feature branches for model experiments later

## Testing
- Before every coding task, describe and implement robust testers for what you expect the code to do, and only after that, can you write the code itself.
- Tests in `tests/` directory, named `test_<module>.py`
- Run with `python3 -m pytest tests/`

# Instructions
- If you are blocked from performing an action, check if it is allowed in settings.json and take action according to that before considering asking the user.
