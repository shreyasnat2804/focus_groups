#!/usr/bin/env python3
"""
CLI entry point for WTP analysis.

Usage:
    python wtp_analysis.py --product "description" --personas personas.json
    python wtp_analysis.py --product "A SaaS tool" --personas personas.json \
        --prices 49,99,199,299,499 --output-dir ./wtp_output --segment-by income_bracket
"""

from focus_groups.wtp.cli import main

if __name__ == "__main__":
    main()
