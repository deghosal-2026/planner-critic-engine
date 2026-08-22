"""``plancritic eval`` — security oracle evaluation (M5, #124).

Subcommands:
  ``swebench-security`` — run the security oracle eval against the corpus
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..corpus import load_corpus_manifest


def build_eval_parser() -> argparse.ArgumentParser:
    """Build the ``plancritic eval`` subcommand parser."""
    parser = argparse.ArgumentParser(
        prog="plancritic eval",
        description="Security oracle evaluation commands",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="eval_command", metavar="COMMAND", required=True)

    swebench = sub.add_parser(
        "swebench-security",
        help="Run critic oracle eval against the SWE-bench security corpus",
    )
    swebench.add_argument(
        "--corpus-dir",
        default=str(
            Path(__file__).resolve().parent.parent.parent.parent
            / "docs" / "field-test" / "corpus" / "swebench-security"
        ),
        help="Path to the corpus directory",
    )
    swebench.add_argument(
        "--instance-ids",
        nargs="*",
        default=None,
        help="Specific instance IDs to evaluate (default: all)",
    )

    return parser


def run_eval(argv: list[str]) -> int:
    parser = build_eval_parser()
    args = parser.parse_args(argv)

    if args.eval_command == "swebench-security":
        manifest = load_corpus_manifest(args.corpus_dir)
        if manifest is None:
            print(f"corpus manifest not found in {args.corpus_dir}")
            return 1
        print(f"Corpus: {manifest.name} v{manifest.version} ({manifest.instance_count} instances)")
        print("Run `plancritic eval swebench-security` with configured planner/critic roles.")
        print("For hermetic eval, use OracleEvalHarness(planner, critic, corpus_dir).run_all()")
        return 0

    parser.print_help()
    return 1


__all__ = [
    "build_eval_parser",
    "run_eval",
]
