"""Field test CLI — ``plancritic field-test run`` (M9).

Drives the field test harness against real goals and real LLMs. Supports
domain batching: pass ``--goals docs/field-test/goals/database/`` to run
only that domain.

Usage::

    # Run all 60 goals
    plancritic field-test run \\
        --goals docs/field-test/goals \\
        --output docs/field-test/reports/20260819

    # Run one domain
    plancritic field-test run \\
        --goals docs/field-test/goals/database \\
        --output docs/field-test/reports/20260819/database
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..loop import LoopConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)


def build_field_test_parser() -> argparse.ArgumentParser:
    """Build the ``field-test`` subcommand parser."""
    parser = argparse.ArgumentParser(
        prog="plancritic field-test",
        description="Field test: run real goals against a real LLM and check invariants",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="field_command", required=True)

    # "run" subcommand
    run_parser = sub.add_parser("run", help="Run the field test sweep")
    run_parser.add_argument(
        "--goals",
        required=True,
        help="Directory containing Goal JSON files (or path to a single goal file)",
    )
    run_parser.add_argument(
        "--output",
        required=True,
        help="Directory to write per-goal traces and summary report",
    )
    run_parser.add_argument(
        "--config",
        default="plancritic.toml",
        help="Provider TOML config path (default: plancritic.toml)",
    )
    run_parser.add_argument(
        "--revision-cap",
        type=int,
        default=4,
        help="Loop revision cap (default: 4)",
    )
    run_parser.add_argument(
        "--critique-mode",
        choices=["heuristic-only", "deterministic-first", "llm-every-revision"],
        default="deterministic-first",
        help="Critique mode (default: deterministic-first)",
    )
    run_parser.add_argument(
        "--save-raw-llm",
        action="store_true",
        help="Save raw LLM provider responses (large, off by default)",
    )

    return parser


def _write_report(summary: dict[str, Any], output_path: Path) -> None:
    """Write the JSON report and a human-readable markdown summary."""
    # JSON
    report_path = output_path / "report.json"
    report_path.write_text(json.dumps(summary, indent=2, default=str))

    # Markdown
    lines = [
        "# Field Test Report",
        "",
        f"**Date:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total:** {summary['total']} goals",
        f"**Passed:** {summary['passed']}",
        f"**Failed:** {summary['failed']}",
        f"**Pass rate:** {summary['pass_rate'] * 100:.0f}%",
        "",
        "## Results",
        "",
        "| Goal | Pass | Status | Reason | Revs | Tasks | Findings |",
        "|------|------|--------|--------|------|-------|----------|",
    ]
    for g in summary.get("goals", []):
        lines.append(
            f"| {g['goal_id']} | "
            f"{'✅' if g['pass'] else '❌'} | "
            f"{g['status']} | "
            f"{g['reason_code'] or '-'} | "
            f"{g['revision_count'] or '-'} | "
            f"{g['task_count']} | "
            f"{g['finding_count']} |"
        )

    md_path = output_path / "report.md"
    md_path.write_text("\n".join(lines) + "\n")

    logger.info("Report written to %s and %s", report_path, md_path)


def run_field_test(argv: list[str]) -> int:
    """Run the field test CLI."""
    parser = build_field_test_parser()
    args = parser.parse_args(argv)

    if args.field_command != "run":
        parser.print_help()
        return 1

    goals_dir = Path(args.goals)
    if not goals_dir.exists():
        logger.error("goals path not found: %s", goals_dir)
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    loop_config = LoopConfig(
        mode=args.critique_mode,
        revision_cap=args.revision_cap,
    )

    from ..field_test_harness import run_sweep

    summary = run_sweep(
        goals_dir=goals_dir,
        output_dir=output_dir,
        config_path=args.config,
        loop_config=loop_config,
        save_raw_llm=args.save_raw_llm,
    )

    _write_report(summary, output_dir)

    if summary["failed"] > 0:
        logger.warning("%d goal(s) failed — see report for details", summary["failed"])
        return 1
    logger.info("All %d goals passed", summary["passed"])
    return 0


__all__ = ["build_field_test_parser", "run_field_test"]