import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Real Estate Assistant CLI - Analyze short-term rental regulations and financials."
    )
    parser.add_argument(
        "prompt",
        type=str,
        help="The target locations to analyze (e.g., 'Austin, TX'). Must be a valid location query.",
    )
    parser.add_argument(
        "--skip-mashvisor",
        action="store_true",
        help="Skip the Mashvisor API call and financial calculations. Returns only legal and compliance data.",
    )
    parser.add_argument(
        "--mock-apis",
        action="store_true",
        help="Use mock data instead of live API calls (useful for testing without consuming API credits).",
    )
    args = parser.parse_args()

    if args.mock_apis:
        os.environ["USE_MOCK_APIS"] = "True"

    from app.agent import load_env_file

    load_env_file()

    if args.mock_apis:
        os.environ["USE_MOCK_APIS"] = "True"

    from app.pipeline import run_pipeline

    print(f"Running analysis for: '{args.prompt}'")
    if args.skip_mashvisor:
        print("Skipping Mashvisor API calls...")
    if args.mock_apis:
        print("Using mock APIs...")

    try:
        report_yaml = run_pipeline(args.prompt, skip_mashvisor=args.skip_mashvisor)
        print("\n--- Final Report ---\n")
        print(report_yaml)
    except Exception as e:
        print(f"\nError running pipeline: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
