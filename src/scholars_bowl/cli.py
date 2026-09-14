"""Small CLI; all paid actions are explicit commands with a cost-estimate threshold."""

import argparse
import csv
import json
import sys
from pathlib import Path

from filelock import Timeout
from openai import APIError

from .corpus import ingest, load_corpus, select_units
from .jobs import (
    api_client,
    collect,
    compare,
    export_job,
    prepare,
    prepare_review,
    recover,
    retry_job,
    run_sync,
    safe_api_error,
    status,
    submit,
)
from .pricing import PROFILES, profile
from .storage import read_json


def default_root():
    for path in [Path.cwd(), *Path.cwd().parents]:
        if (path / "datasets.json").is_file():
            return path
    return Path.cwd()


def model_options(parser, default="luna", tokens=8000):
    parser.add_argument("--profile", choices=PROFILES, default=default)
    parser.add_argument(
        "--model", help="Override model ID; requires explicit standard token prices"
    )
    parser.add_argument("--input-rate", type=float, help="Standard USD per million input tokens")
    parser.add_argument("--output-rate", type=float, help="Standard USD per million output tokens")
    parser.add_argument(
        "--reasoning",
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
        help="Only for models supporting reasoning.effort",
    )
    parser.add_argument("--max-output-tokens", type=int, default=tokens)


def build_parser():
    parser = argparse.ArgumentParser(prog="qb", description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root(),
        help="Repository containing datasets.json and .env",
    )
    parser.add_argument("--data-dir", type=Path, help="Artifacts directory (default: ROOT/data)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "ingest", help="Import all CSVs into a versioned local snapshot; no API calls"
    )
    commands.add_parser("corpus", help="Show current corpus counts and anomalies")
    doctor = commands.add_parser(
        "doctor", help="Check key presence and optionally authenticate without generation"
    )
    doctor.add_argument(
        "--online", action="store_true", help="Check configured baseline model access via API"
    )
    commands.add_parser("jobs", help="List local jobs without API calls")
    plan = commands.add_parser("prepare", help="Write a reviewable extraction job; no model calls")
    model_options(plan)
    selection = plan.add_mutually_exclusive_group()
    selection.add_argument("--limit", type=int, default=36, help="Sample size (default: 36)")
    selection.add_argument("--all", action="store_true", help="Select the full eligible corpus")
    plan.add_argument(
        "--offset", type=int, default=0, help="Skip this many units in deterministic sample order"
    )
    plan.add_argument("--seed", type=int, default=42)
    plan.add_argument("--level", choices=["both", "middle-school", "high-school"], default="both")
    plan.add_argument("--kind", choices=["both", "tossup", "bonus"], default="both")
    sync = commands.add_parser("smoke", help="Run a small synchronous trial; standard API rates")
    sync.add_argument("job")
    sync.add_argument("--limit", type=int, default=2)
    sync.add_argument("--workers", type=int, default=1, help="Concurrent requests (1-8)")
    sync.add_argument(
        "--max-cost",
        type=float,
        required=True,
        help="Reject if padded estimated USD exceeds this threshold",
    )
    run = commands.add_parser(
        "run", help="Run a synchronous pilot; reserve Batch for large-scale processing"
    )
    run.add_argument("job")
    run.add_argument("--limit", type=int, default=36)
    run.add_argument("--workers", type=int, default=1, help="Concurrent requests (1-8)")
    run.add_argument("--max-cost", type=float, required=True)
    batch = commands.add_parser(
        "submit", help="Upload pending requests and create a paid Batch job"
    )
    batch.add_argument("job")
    batch.add_argument("--max-cost", type=float, required=True)
    stat = commands.add_parser(
        "status", help="Check Batch progress once; no background worker required"
    )
    stat.add_argument("job")
    stat.add_argument("--offline", action="store_true")
    get = commands.add_parser(
        "collect", help="Download and validate completed/partial terminal results"
    )
    get.add_argument("job")
    recovery = commands.add_parser(
        "recover", help="Recover an uncertain submission without resubmitting"
    )
    recovery.add_argument("job")
    recovery.add_argument("--batch-id")
    retry = commands.add_parser(
        "retry", help="Prepare a new job containing only unvalidated requests"
    )
    retry.add_argument("job")
    review = commands.add_parser(
        "review", help="Prepare a blinded larger-model review of validated extractions"
    )
    review.add_argument("job")
    model_options(review, default="reviewer", tokens=6000)
    report = commands.add_parser("report", help="Export source-linked results and a local summary")
    report.add_argument("job")
    comparison = commands.add_parser(
        "compare", help="Compare extraction jobs and their model reviews on the same sample"
    )
    comparison.add_argument("jobs", nargs="+")
    return parser


def execute(args):
    root = args.root.resolve()
    data = (args.data_dir or root / "data").resolve()
    if args.command == "ingest":
        return ingest(root, data)
    if args.command == "corpus":
        return load_corpus(data)[0]
    if args.command == "doctor":
        client = api_client(root)
        result = {"key_present": True, "key_value": "never displayed"}
        if args.online:
            result["accessible_models"] = [
                client.models.retrieve(p["model"]).id for p in PROFILES.values()
            ]
        return result
    if args.command == "jobs":
        return [
            {
                "job": p.parent.name,
                "stage": (plan := read_json(p))["stage"],
                "model": plan["rates"]["model"],
                "requests": len(plan["requests"]),
            }
            for p in sorted((data / "jobs").glob("*/plan.json"))
        ]
    if args.command in {"prepare", "review"}:
        rates = profile(args.profile, args.model, args.input_rate, args.output_rate)
        if args.command == "prepare":
            if args.limit <= 0 or args.offset < 0:
                raise ValueError("--limit must be positive and --offset nonnegative")
            manifest, units = load_corpus(data)
            units = [
                u
                for u in units
                if (args.level == "both" or u["level"] == args.level)
                and (args.kind == "both" or u["kind"] == args.kind)
            ]
            units = select_units(units, limit=None, seed=args.seed)
            units = (
                units[args.offset :] if args.all else units[args.offset : args.offset + args.limit]
            )
            job_id, budget = prepare(
                data,
                units,
                rates,
                manifest["snapshot"],
                args.max_output_tokens,
                reasoning=args.reasoning,
            )
        else:
            job_id, budget = prepare_review(
                data, args.job, rates, args.max_output_tokens, args.reasoning
            )
        return {"job": job_id, "directory": str(data / "jobs" / job_id), "budget": budget}
    if args.command in {"smoke", "run"}:
        return run_sync(root, data, args.job, args.limit, args.max_cost, workers=args.workers)
    if args.command == "submit":
        return submit(root, data, args.job, args.max_cost)
    if args.command == "status":
        return status(root, data, args.job, refresh=not args.offline)
    if args.command == "collect":
        return collect(root, data, args.job)
    if args.command == "recover":
        return recover(root, data, args.job, args.batch_id)
    if args.command == "retry":
        return retry_job(data, args.job)
    if args.command == "report":
        return export_job(data, args.job)
    if args.command == "compare":
        return compare(data, args.jobs)
    raise ValueError("Unknown command")


def main():
    args = build_parser().parse_args()
    try:
        print(json.dumps(execute(args), indent=2, ensure_ascii=False))
    except APIError as exc:
        print(safe_api_error(exc), file=sys.stderr)
        raise SystemExit(1) from None
    except Timeout:
        print("Another process is changing this job; retry after it finishes.", file=sys.stderr)
        raise SystemExit(1) from None
    except (ValueError, OSError, KeyError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
