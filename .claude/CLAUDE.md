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
- **Frontend**: React 19 + Vite + React Router 7 (plain CSS with design tokens)
- **Deployment**: Render (render.yaml blueprint, `prod` branch)

## Architecture

```
Reddit (PRAW) → Postgres (raw posts)
  → Demographic Tagger (3-layer) → tagged posts
  → sentence-transformers → pgvector embeddings
  → LoRA fine-tune (per sector) → sector models
  → FastAPI backend → React frontend
```

## Frontend Structure

- **Routing**: `/` landing page (redirects onboarded users to `/dashboard`), `/dashboard` pitch list, `/new` create pitch, `/sessions/:id` results, `/onboarding` onboarding flow, `/about` about page
- **Styling**: Single global CSS file `frontend/src/index.css` using CSS custom properties (design tokens). No CSS modules, no Tailwind. Fonts: DM Sans (body), Space Grotesk (display), Instrument Serif (accent)
- **Testing**: Vitest + Testing Library. Tests colocated with components (`__tests__/` dirs or `.test.jsx` siblings)
- **Key patterns**: `localStorage` keys prefixed with `focustest_` (e.g. `focustest_onboarded`, `focustest_preferred_sector`). Constants in `src/constants.js`. API layer in `src/api.js` with `VITE_API_URL` env var
- **Nav**: `AppNav` component in `App.jsx` is hidden on `/` and `/onboarding`. Landing page has its own nav

## Deployment

- **Render** via `render.yaml` at repo root, watching `prod` branch
- **Services**: `fg-api` (FastAPI/Docker), `fg-web` (React/nginx/Docker), `fg-db` (Postgres 16)
- **Deploy flow**: merge to `main` → merge `main` into `prod` → push `prod` → Render auto-deploys
- Frontend-only changes only require `fg-web` redeployment. Backend-only changes only require `fg-api`

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-17 | Postgres + pgvector over SQLite | Need vector similarity search + concurrent access for API |
| 2026-02-17 | Mistral-7B base over Llama 3.1 8B | Better instruction following at similar size, permissive license |
| 2026-02-17 | 3 sector models over 1 general model | Domain-specific fine-tuning yields better predictions per sector |
| 2026-02-17 | Lambda GPU over Colab for training | Persistent SSH, no session timeouts, better for LoRA jobs |
| 2026-03-15 | Route `/` is landing page, `/dashboard` is app | Separate marketing surface from authenticated app experience |

## Git Workflow

- Commit regularly and logically — each commit should represent one coherent codebase change (e.g. "add tests for X", "implement X module", "update imports for X"). Don't batch unrelated changes into one commit, and don't wait until the end of a prompt to commit everything at once.
- Push to remote at the end of every prompt, after all commits are made
- Use `git revert` if something breaks — no force-push or history rewriting
- Feature branches off `prod`, PR to `main`, merge `main` into `prod` for deploy
- When creating PRs, use a simple `--body` string (no heredocs or multiline) — heredocs in `gh pr create` get blocked by dontAsk mode

## Testing

- Before every coding task, describe and implement robust testers for what you expect the code to do, and only after that, can you write the code itself.
- **Backend**: Tests in `tests/` directory, named `test_<module>.py`. Run with `python3 -m pytest tests/`
- **Frontend**: Tests colocated with source. Run with `npx vitest run` from `frontend/`. Currently 92 tests across 10 files

## Shell & Permissions

- The repo uses `dontAsk` permission mode. Check `.claude/settings.json` for allowed patterns before running commands
- Working directory is often `frontend/` after running npm/vitest commands — use relative paths for `git add` accordingly (e.g. `git add src/App.jsx` not `git add frontend/src/App.jsx`)
- Git commands must start with `git` (not `cd ... && git ...`) to match the allow pattern `Bash(git *)`
- `gh pr create` with heredoc body is blocked — use simple inline `--body "..."` strings
- Multiline `git commit -m` with heredocs may be blocked — use single-line messages or short multiline with escaped newlines

## Self-Improvement Protocol

**At the end of every prompt**, before responding to the user, reflect on what happened during the conversation and update this file if anything new was learned that would help future agents. This includes:

- New architectural decisions, routing changes, or structural shifts
- Shell/permission gotchas that caused failures
- Deployment learnings (which services need redeploying for which changes)
- Testing patterns or conventions that evolved
- Any corrections or feedback from the user

If nothing noteworthy happened, that's fine — skip the update. The bar is: "would a future agent waste time or make a mistake without this information?" If yes, add it. If no, move on.

# Instructions
- If you are blocked from performing an action, check if it is allowed in settings.json and take action according to that before considering asking the user.
