"""
CLI runner for focus group sessions.

Usage:
    python -m focus_groups.cli_runner \
        --question "What do you think about AI in hiring?" \
        --sector tech --num-personas 5

Optional --no-save to skip DB storage.
"""

from __future__ import annotations

import argparse
import sys
from io import StringIO

from focus_groups.export import export_csv, export_pdf
from focus_groups.personas.selection import select_personas
from focus_groups.claude import get_client, run_focus_group
from focus_groups.db import get_conn
from focus_groups.sessions import create_session, save_responses, complete_session, fail_session, get_session


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a synthetic focus group session.")
    parser.add_argument("--question", default=None, help="The focus group question (required for run mode).")
    parser.add_argument("--sector", default=None, help="Sector filter: tech, financial, political.")
    parser.add_argument("--num-personas", type=int, default=5, help="Number of personas (default 5).")
    parser.add_argument("--no-save", action="store_true", help="Skip saving results to DB.")
    parser.add_argument("--session-id", type=str, default=None, help="Session ID (UUID) for export (use with --export-csv/--export-pdf).")
    parser.add_argument("--export-csv", default=None, metavar="PATH", help="Export session to CSV file.")
    parser.add_argument("--export-pdf", default=None, metavar="PATH", help="Export session to PDF file.")
    return parser.parse_args(argv)


def run_pipeline(
    question: str,
    sector: str | None,
    num_personas: int,
    save: bool = True,
    output=None,
) -> None:
    """
    Full focus group pipeline: select personas → call Claude → print/store.

    Args:
        question:     The focus group question
        sector:       Optional sector filter
        num_personas: Number of personas to select
        save:         Whether to persist session to DB
        output:       Writable file-like object for output (default: sys.stdout)
    """
    if output is None:
        output = sys.stdout

    conn = get_conn()

    # 1. Select personas
    print(f"Selecting {num_personas} personas (sector={sector})...", file=output)
    cards = select_personas(conn, sector=sector, n=num_personas)

    if not cards:
        print("No personas found matching the given filters.", file=output)
        conn.close()
        return

    print(f"Selected {len(cards)} personas.\n", file=output)

    # 2. Run focus group
    print("Running focus group through Claude...\n", file=output)
    client = get_client()
    responses = run_focus_group(client, cards, question)

    # 3. Print results
    print("=" * 60, file=output)
    print(f"FOCUS GROUP: {question}", file=output)
    print("=" * 60, file=output)

    for i, r in enumerate(responses, 1):
        print(f"\n--- Persona {i}: {r['persona_summary']} ---", file=output)
        print(r["response_text"], file=output)

    print(f"\n{'=' * 60}", file=output)
    print(f"Total responses: {len(responses)}", file=output)

    # 4. Save to DB
    if save:
        session_id = create_session(conn, sector, {}, num_personas, question)
        save_responses(conn, session_id, responses)
        complete_session(conn, session_id)
        print(f"Session saved: id={session_id}", file=output)

    conn.close()


def export_session(session_id: str, csv_path: str | None, pdf_path: str | None) -> None:
    """Fetch a session from DB and write CSV/PDF exports to disk."""
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
    finally:
        conn.close()

    if session is None:
        print(f"Session {session_id} not found.")
        return

    if csv_path:
        with open(csv_path, "w") as f:
            f.write(export_csv(session))
        print(f"CSV exported to {csv_path}")

    if pdf_path:
        with open(pdf_path, "wb") as f:
            f.write(export_pdf(session))
        print(f"PDF exported to {pdf_path}")


def main():
    args = parse_args()

    # Export mode: --session-id with --export-csv/--export-pdf
    if args.session_id is not None:
        export_session(args.session_id, args.export_csv, args.export_pdf)
        return

    if args.question is None:
        print("Error: --question is required for run mode.")
        sys.exit(1)

    run_pipeline(
        question=args.question,
        sector=args.sector,
        num_personas=args.num_personas,
        save=not args.no_save,
    )


if __name__ == "__main__":
    main()
