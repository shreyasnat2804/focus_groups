# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Predictive sentiment validation system. Scrapes demographically-tagged social media posts (pre-2024), fine-tunes an LLM, then validates predictions against actual 2024-2025 product launch reactions. Goal: prove >0.6 correlation between predicted and actual sentiment by demographic.

## Tech Stack

- **Data collection**: Python, PRAW (Reddit), requests
- **Storage**: SQLite (`demographics_corpus.db`)
- **ML**: Hugging Face Transformers, PyTorch, LoRA fine-tuning (Llama 3.1 8B or Mistral 7B)
- **Analysis**: Pandas, Matplotlib, Jupyter notebooks
- **Report**: Markdown → PDF

## Key Deliverables

- `demographics_corpus.db` — 100k demographically-tagged posts
- `test_cases.json` — 10 product launches with ground truth sentiment
- `demographic_model/` — fine-tuned LoRA weights
- `predictions.json` — model predictions (generated blind to actuals)
- `validation_report.pdf` — correlation analysis and methodology
- `analysis.ipynb` — reproducible validation notebook

## Architecture

Six-phase pipeline, each phase feeding the next:

1. **Data Collection** → SQLite corpus with schema: `[post_id, text, demographic_tags, timestamp, source]`
2. **Test Case Selection** → Ground truth: `[product, demographic, actual_sentiment_distribution]`
3. **Model Training** → LoRA fine-tune with demographic conditioning tokens
4. **Prediction Generation** → Batch inference, 10x sampling per case for distributions
5. **Validation Analysis** → Correlation, error breakdown, significance tests
6. **Refinement** — Only if correlation is 0.4-0.6

## Git Workflow

- Commit and push to `main` after every meaningful change
- Use descriptive commit messages
- If something breaks, use `git revert` — don't force-push or rewrite history
- Switch to feature branches later when experimenting (different models, prompting strategies)

## Development Notes

- Demographic extraction (age/gender/income from bios/posts) uses an NLP classifier — this is the noisiest component
- Predictions must be saved before comparing to actuals to avoid bias
- Twitter/X scraping is out of scope for MVP (API cost)
- No web interface, auth, or real-time API — batch processing only