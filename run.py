#!/usr/bin/env python3
import argparse
import sys

from agentbench import benchmark, runner

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


def _add_provider_flags(parser: argparse.ArgumentParser) -> None:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AgentBench -- local benchmark runner"
    )
    parser.add_argument("task_id", help="Identifier of the task to run")
    _add_provider_flags(parser)
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of times to repeat the task run (default: 1)",
    )
    return parser


def build_benchmark_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AgentBench -- run every task under tasks/"
    )
    _add_provider_flags(parser)
    return parser


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    try:
        if argv and argv[0] == "benchmark":
            args = build_benchmark_parser().parse_args(argv[1:])
            provider_name = args.provider or DEFAULT_PROVIDER
            model = args.model or DEFAULT_MODEL
            benchmark.run_benchmark(
                provider_name,
                model,
                keep_workspace=args.keep_workspace,
                verbose=args.verbose,
            )
            return 0

        args = build_parser().parse_args(argv)
        provider_name = args.provider or DEFAULT_PROVIDER
        model = args.model or DEFAULT_MODEL

        if args.runs > 1:
            results = []
            for i in range(args.runs):
                print(f"\n--- Run {i + 1}/{args.runs} ---")
                result = runner.run_single_task(
                    args.task_id,
                    provider_name,
                    model,
                    keep_workspace=args.keep_workspace,
                    verbose=args.verbose,
                )
                results.append(result)
            records = [
                benchmark.record_from_result(args.task_id, r) for r in results
            ]
            aggregate = benchmark.aggregate_repeated_runs(records)
            print(
                "\n"
                + benchmark.format_repeated_runs_summary(aggregate)
            )
            return 0 if aggregate["num_successful"] == aggregate["num_runs"] else 1

        result = runner.run_single_task(
            args.task_id,
            provider_name,
            model,
            keep_workspace=args.keep_workspace,
            verbose=args.verbose,
        )
        return 0 if result["evaluation"]["task_success"] else 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
