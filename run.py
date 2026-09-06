#!/usr/bin/env python3
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="AgentBench — local benchmark runner"
    )
    parser.add_argument("task_id", help="Identifier of the task to run")
    args = parser.parse_args()
    print("not implemented yet")


if __name__ == "__main__":
    main()
