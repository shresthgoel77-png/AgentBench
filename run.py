#!/usr/bin/env python3
import argparse
import sys

from agentbench import runner

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AgentBench -- local benchmark runner"
    )
    parser.add_argument("task_id", help="Identifier of the task to run")
    parser.add_argument(
        "--model",
        default=None,
        help="Model to use (provider-specific model name)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="LLM provider name (default: anthropic)",
    )
    parser.add_argument(
        "--keep-workspace",
        action="store_true",
        help="Leave the run workspace in place after the run",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each trajectory step as it is recorded",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    provider_name = args.provider or DEFAULT_PROVIDER
    model = args.model or DEFAULT_MODEL
    result = runner.run_single_task(
        args.task_id,
        provider_name,
        model,
        keep_workspace=args.keep_workspace,
        verbose=args.verbose,
    )
    return 0 if result["evaluation"]["task_success"] else 1


if __name__ == "__main__":
    sys.exit(main())
