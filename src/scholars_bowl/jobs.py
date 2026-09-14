"""Inspectable job plans, restart-safe submission, cached results, and review reports."""

import json
import math
import os
import uuid
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from dotenv import dotenv_values
from filelock import FileLock
from openai import APIError, OpenAI
from pydantic import ValidationError

from .extraction import (
    EXTRACT_PROMPT,
    PROMPT_VERSION,
    REVIEW_PROMPT,
    REVIEW_VERSION,
    extraction_schema,
    payload,
    review_schema,
    validate_extraction,
    validate_review,
)
from .pricing import estimate, usage_cost
from .storage import (
    atomic_text,
    digest,
    dumps,
    file_hash,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)

TERMINAL = {"completed", "failed", "expired", "cancelled"}


def api_client(root):
    # Do not load unrelated env variables or print secrets. Existing environment wins.
    key = os.environ.get("OPENAI_API_KEY") or dotenv_values(Path(root) / ".env").get(
        "OPENAI_API_KEY"
    )
    if not key or not key.strip():
        raise ValueError("OPENAI_API_KEY is missing from the environment and project .env")
    # Batch creation is deliberately not automatically retried after an uncertain response.
    return OpenAI(
        api_key=key.strip(), base_url="https://api.openai.com/v1", max_retries=0, timeout=90
    )


def safe_api_error(exc):
    # Authentication errors can echo the supplied key. Never print API exception text.
    status = getattr(exc, "status_code", None)
    hints = {
        401: "Check the key in .env.",
        403: "Check project/model permissions.",
        429: "Check API quota, billing, and rate limits.",
        400: "Check the job request schema and model compatibility in the API dashboard.",
    }
    return f"OpenAI {type(exc).__name__} (HTTP {status or 'unavailable'}). " + hints.get(
        status, "Retry status/recovery after checking connectivity."
    )


def request_for(unit, rates, max_output_tokens, candidate=None, reasoning=None):
    stage = "review" if candidate is not None else "extract"
    content = {"source": payload(unit)}
    if candidate is not None:
        content["candidate"] = candidate
    schema = review_schema(unit) if stage == "review" else extraction_schema(unit)
    body = {
        "model": rates["model"],
        "store": False,
        "instructions": REVIEW_PROMPT if stage == "review" else EXTRACT_PROMPT,
        "input": dumps(content),
        "max_output_tokens": max_output_tokens,
        "text": {
            "format": {"type": "json_schema", "name": stage, "strict": True, "schema": schema}
        },
    }
    if reasoning or rates.get("reasoning"):
        body["reasoning"] = {"effort": reasoning or rates["reasoning"]}
    fingerprint = digest(
        [PROMPT_VERSION if stage == "extract" else REVIEW_VERSION, unit["id"], body]
    )
    return {
        "custom_id": "r_" + fingerprint[:60],
        "method": "POST",
        "url": "/v1/responses",
        "body": body,
    }


def prepare(data, units, rates, snapshot, max_output_tokens=4000, candidates=None, reasoning=None):
    if not units:
        raise ValueError("No eligible source units selected")
    if max_output_tokens < 128:
        raise ValueError("Output token cap must be at least 128")
    tasks, requests = {}, []
    stage = "review" if candidates is not None else "extract"
    for unit in units:
        candidate = candidates[unit["id"]] if candidates is not None else None
        request = request_for(
            unit, rates, max_output_tokens, candidate["result"] if candidate else None, reasoning
        )
        custom_id = request["custom_id"]
        if custom_id in tasks:
            raise ValueError("Duplicate unit selected for a job")
        tasks[custom_id] = {
            "unit": unit,
            "candidate_request_id": candidate["custom_id"] if candidate else None,
        }
        requests.append(request)
    plan = {
        "version": 1,
        "stage": stage,
        "snapshot": snapshot,
        "rates": rates,
        "prompt_version": PROMPT_VERSION if stage == "extract" else REVIEW_VERSION,
        "tasks": tasks,
        "requests": requests,
    }
    job_id = digest(plan)[:24]
    job = Path(data) / "jobs" / job_id
    job.mkdir(parents=True, exist_ok=True)
    with FileLock(str(job / ".lock"), timeout=1):
        if not (job / "plan.json").exists():
            write_jsonl(job / "requests.jsonl", requests)
            write_json(job / "plan.json", plan)
    return job_id, estimate(requests, rates, batch=False)


def load_job(data, job_id):
    if len(job_id) != 24 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("Invalid local job ID")
    job = Path(data) / "jobs" / job_id
    plan = read_json(job / "plan.json")
    if digest(plan)[:24] != job_id:
        raise ValueError("Job plan was modified; prepare a new job instead")
    if list(read_jsonl(job / "requests.jsonl")) != plan["requests"]:
        raise ValueError("Request file differs from the immutable job plan")
    return job, plan


def result_path(data, custom_id):
    return Path(data) / "cache" / (custom_id + ".json")


def result_for(data, custom_id):
    path = result_path(data, custom_id)
    return read_json(path) if path.exists() else None


def pending(data, plan):
    return [r for r in plan["requests"] if result_for(data, r["custom_id"]) is None]


def check_inflight(data, job_id, requests):
    ids = {r["custom_id"] for r in requests}
    for path in (Path(data) / "jobs").glob("*/remote.json"):
        if path.parent.name == job_id:
            continue
        remote = read_json(path)
        if not (remote.get("batch_id") or remote.get("creating")):
            continue
        status_path = path.parent / "batch-status.json"
        if (
            status_path.exists()
            and read_json(status_path)["status"] in TERMINAL
            and (path.parent / "collection.json").exists()
        ):
            continue
        if ids.intersection(remote["custom_ids"]):
            raise ValueError(
                f"Overlapping requests belong to Batch job {path.parent.name}; collect or recover it first"
            )


def check_budget(requests, rates, max_cost, batch):
    budget = estimate(requests, rates, batch=batch)
    if (
        not math.isfinite(max_cost)
        or max_cost <= 0
        or budget["estimated_usd_at_output_cap"] > max_cost
    ):
        raise ValueError(
            f"Estimated cost at output cap ${budget['estimated_usd_at_output_cap']:.4f} exceeds --max-cost ${max_cost:.4f}"
        )
    return budget


def accept_result(data, plan, custom_id, body, batch):
    if body.get("status") != "completed":
        raise ValueError("Response incomplete, failed, or truncated")
    chunks = [
        c
        for item in body.get("output", [])
        if item.get("type") == "message"
        for c in item.get("content", [])
    ]
    if any(c.get("type") == "refusal" for c in chunks):
        raise ValueError("Model refused the request")
    text = "".join(c.get("text", "") for c in chunks if c.get("type") == "output_text")
    value = json.loads(text)
    unit = plan["tasks"][custom_id]["unit"]
    if plan["stage"] == "extract":
        value, spans = validate_extraction(value, unit, plan["prompt_version"])
    else:
        value, spans = validate_review(value, unit), []
    result = {
        "custom_id": custom_id,
        "unit_id": unit["id"],
        "stage": plan["stage"],
        "model_requested": plan["rates"]["model"],
        "model_returned": body.get("model"),
        "response_id": body.get("id"),
        "prompt_version": plan["prompt_version"],
        "usage": body.get("usage") or {},
        "batch": batch,
        "result": value,
        "evidence_spans": spans,
    }
    result["estimated_usage_cost_usd"] = usage_cost(result["usage"], plan["rates"], batch)
    write_json(result_path(data, custom_id), result)
    return result


def run_sync(root, data, job_id, limit, max_cost, client=None, workers=1):
    """Small synchronous experiments only. Successful requests are reused by Batch submission."""
    job, plan = load_job(data, job_id)
    if not 1 <= workers <= 8:
        raise ValueError("Synchronous workers must be between 1 and 8")
    if not 1 <= limit <= 500:
        raise ValueError(
            "Synchronous pilots require --limit between 1 and 500; use Batch for large-scale work"
        )
    with (
        FileLock(str(Path(data) / ".execution.lock"), timeout=1),
        FileLock(str(job / ".lock"), timeout=1),
    ):
        if (job / "remote.json").exists():
            raise ValueError("This job already has a Batch submission; collect it before retrying")
        requests = pending(data, plan)[:limit]
        check_inflight(data, job_id, requests)
        budget = check_budget(requests, plan["rates"], max_cost, batch=False)
        client = client or api_client(root)

        def process(request):
            custom_id = request["custom_id"]
            raw_path = job / "sync" / (custom_id + ".json")
            # A saved raw response is replayed without charging again, including invalid outputs.
            if raw_path.exists():
                body = read_json(raw_path)
            else:
                body = client.responses.create(**request["body"]).model_dump(mode="json")
                write_json(raw_path, body)
            try:
                accept_result(data, plan, custom_id, body, batch=False)
            except (ValueError, ValidationError) as exc:
                write_json(
                    job / "validation" / (custom_id + ".json"), {"error": validation_error(exc)}
                )

        # Bounded ordinary Responses requests, not Batch. Persist each result even
        # if another worker fails; stop scheduling new work on an API error.
        with ThreadPoolExecutor(max_workers=workers) as executor:
            remaining = iter(requests)
            active = {
                executor.submit(process, request)
                for request in [next(remaining, None) for _ in range(workers)]
                if request is not None
            }
            while active:
                done, active = wait(active, return_when=FIRST_COMPLETED)
                for future in done:
                    future.result()
                for _ in done:
                    request = next(remaining, None)
                    if request is not None:
                        active.add(executor.submit(process, request))
        return {
            "job": job_id,
            "attempted": len(requests),
            "valid_total": len(plan["requests"]) - len(pending(data, plan)),
            "budget": budget,
        }


def validation_error(exc):
    if isinstance(exc, ValidationError):
        return "Schema validation failed: " + ", ".join(
            ".".join(map(str, e["loc"])) for e in exc.errors()
        )
    if isinstance(exc, json.JSONDecodeError):
        return "Response did not contain valid JSON"
    return str(exc)


def submit(root, data, job_id, max_cost, client=None):
    job, plan = load_job(data, job_id)
    with (
        FileLock(str(Path(data) / ".execution.lock"), timeout=1),
        FileLock(str(job / ".lock"), timeout=1),
    ):
        remote_path = job / "remote.json"
        if remote_path.exists():
            remote = read_json(remote_path)
            if remote.get("batch_id"):
                return {"job": job_id, "batch_id": remote["batch_id"], "already_submitted": True}
            if remote.get("creating"):
                raise ValueError(
                    "Submission outcome is uncertain. Run recover; do not submit a duplicate job."
                )
        else:
            requests = pending(data, plan)
            if not requests:
                return {
                    "job": job_id,
                    "message": "All requests already have validated cached results",
                }
            if len(requests) > 50_000:
                raise ValueError("Batch exceeds 50,000 requests; prepare smaller samples")
            check_budget(requests, plan["rates"], max_cost, batch=True)
            check_inflight(data, job_id, requests)
            write_jsonl(job / "batch-input.jsonl", requests)
            if (job / "batch-input.jsonl").stat().st_size > 190_000_000:
                raise ValueError("Batch input exceeds the conservative 190 MB limit")
            remote = {
                "custom_ids": [r["custom_id"] for r in requests],
                "input_sha256": file_hash(job / "batch-input.jsonl"),
                "submission_tag": uuid.uuid4().hex,
                "creating": False,
            }
            write_json(remote_path, remote)
        requests_by_id = {r["custom_id"]: r for r in plan["requests"]}
        selected = [requests_by_id[cid] for cid in remote["custom_ids"]]
        check_inflight(data, job_id, selected)
        budget = check_budget(selected, plan["rates"], max_cost, batch=True)
        if file_hash(job / "batch-input.jsonl") != remote["input_sha256"]:
            raise ValueError("Batch input changed after preparation")
        client = client or api_client(root)
        if not remote.get("input_file_id"):
            with (job / "batch-input.jsonl").open("rb") as stream:
                remote["input_file_id"] = client.files.create(file=stream, purpose="batch").id
            write_json(remote_path, remote)
        # Persist intent before the request; recovery searches metadata after timeouts/crashes.
        remote["creating"] = True
        write_json(remote_path, remote)
        try:
            batch = client.batches.create(
                input_file_id=remote["input_file_id"],
                endpoint="/v1/responses",
                completion_window="24h",
                metadata={"qb_job": job_id, "qb_submission": remote["submission_tag"]},
            )
        except APIError as exc:
            if getattr(exc, "status_code", None) in {400, 401, 403, 404, 422, 429}:
                remote["creating"] = False  # Explicit rejection, not an uncertain server outcome.
                write_json(remote_path, remote)
            raise
        remote.update(batch_id=batch.id, creating=False)
        write_json(remote_path, remote)
        write_json(job / "batch-status.json", batch.model_dump(mode="json"))
        return {"job": job_id, "batch_id": batch.id, "status": batch.status, "budget": budget}


def recover(root, data, job_id, batch_id=None, client=None):
    job, _ = load_job(data, job_id)
    with FileLock(str(job / ".lock"), timeout=1):
        remote = read_json(job / "remote.json")
        client = client or api_client(root)
        if remote.get("batch_id"):
            return {"batch_id": remote["batch_id"], "already_recovered": True}
        batches = (
            [client.batches.retrieve(batch_id)] if batch_id else client.batches.list(limit=100)
        )
        matches = [
            b
            for b in batches
            if (b.metadata or {}).get("qb_submission") == remote["submission_tag"]
            and (b.metadata or {}).get("qb_job") == job_id
            and b.input_file_id == remote.get("input_file_id")
        ]
        if len(matches) != 1:
            raise ValueError(
                "Recovery could not identify exactly one matching batch. Check the API dashboard; no resubmission was made."
            )
        remote.update(batch_id=matches[0].id, creating=False)
        write_json(job / "remote.json", remote)
        return {"job": job_id, "batch_id": matches[0].id, "recovered": True}


def status(root, data, job_id, refresh=True, client=None):
    job, plan = load_job(data, job_id)
    result = {
        "job": job_id,
        "stage": plan["stage"],
        "model": plan["rates"]["model"],
        "requests": len(plan["requests"]),
        "validated": len(plan["requests"]) - len(pending(data, plan)),
    }
    if (job / "remote.json").exists():
        remote = read_json(job / "remote.json")
        result["batch_id"] = remote.get("batch_id")
        if refresh and remote.get("batch_id"):
            client = client or api_client(root)
            batch = client.batches.retrieve(remote["batch_id"]).model_dump(mode="json")
            write_json(job / "batch-status.json", batch)
        elif (job / "batch-status.json").exists():
            batch = read_json(job / "batch-status.json")
        else:
            batch = {"status": "submission_uncertain" if remote["creating"] else "not_submitted"}
        result["status"] = batch["status"]
        result["request_counts"] = batch.get("request_counts")
    else:
        result["status"] = "local"
    return result


def collect(root, data, job_id, client=None):
    job, _ = load_job(data, job_id)
    with FileLock(str(job / ".lock"), timeout=1):
        client = client or api_client(root)
        info = status(root, data, job_id, client=client)
        if info["status"] not in TERMINAL:
            return {**info, "message": "Batch is not terminal; collect again later"}
        batch = read_json(job / "batch-status.json")
        for field, filename in (
            ("output_file_id", "batch-output.jsonl"),
            ("error_file_id", "batch-errors.jsonl"),
        ):
            if batch.get(field) and not (job / filename).exists():
                atomic_text(job / filename, client.files.content(batch[field]).text)
        return import_results(data, job_id)


def import_results(data, job_id):
    """Join unordered outputs by custom_id; never cache invalid, refused, or incomplete results."""
    job, plan = load_job(data, job_id)
    remote = read_json(job / "remote.json")
    expected = set(remote["custom_ids"])
    seen, rows, errors = set(), [], []
    for filename in ("batch-output.jsonl", "batch-errors.jsonl"):
        if (job / filename).exists():
            rows.extend(read_jsonl(job / filename))
    # Reject ambiguous or foreign outputs before accepting any of this download.
    for row in rows:
        cid = row.get("custom_id")
        if cid not in expected or cid in seen:
            raise ValueError("Unexpected or duplicate custom_id in Batch results")
        seen.add(cid)
    for row in rows:
        cid = row["custom_id"]
        response = row.get("response") or {}
        if row.get("error") or response.get("status_code") != 200:
            errors.append(
                {
                    "custom_id": cid,
                    "error": "API request failed",
                    "status_code": response.get("status_code"),
                }
            )
            continue
        if result_for(data, cid):
            continue
        try:
            accept_result(data, plan, cid, response["body"], batch=True)
        except (ValueError, ValidationError) as exc:
            errors.append({"custom_id": cid, "error": validation_error(exc)})
    errors.extend(
        {"custom_id": cid, "error": "No result returned"} for cid in sorted(expected - seen)
    )
    summary = {
        "job": job_id,
        "validated": len(plan["requests"]) - len(pending(data, plan)),
        "total": len(plan["requests"]),
        "errors": errors,
    }
    write_json(job / "collection.json", summary)
    return summary


def retry_job(data, job_id):
    job, plan = load_job(data, job_id)
    if (job / "remote.json").exists():
        batch = read_json(job / "batch-status.json")
        if batch["status"] not in TERMINAL or not (job / "collection.json").exists():
            raise ValueError("Collect the terminal batch before preparing a retry")
    requests = pending(data, plan)
    if not requests:
        raise ValueError("No unvalidated requests to retry")
    # Include parent identity so even a total failure creates a separate job directory.
    new_plan = {
        **plan,
        "requests": requests,
        "tasks": {r["custom_id"]: plan["tasks"][r["custom_id"]] for r in requests},
        "retry_of": job_id,
    }
    new_id = digest(new_plan)[:24]
    new_job = Path(data) / "jobs" / new_id
    new_job.mkdir(parents=True, exist_ok=True)
    with FileLock(str(new_job / ".lock"), timeout=1):
        write_jsonl(new_job / "requests.jsonl", requests)
        write_json(new_job / "plan.json", new_plan)
    return {"job": new_id, "requests": len(requests), "budget": estimate(requests, plan["rates"])}


def prepare_review(data, job_id, rates, max_output_tokens=6000, reasoning=None):
    _, plan = load_job(data, job_id)
    if plan["stage"] != "extract":
        raise ValueError("Review requires an extraction job")
    units, candidates = [], {}
    for request in plan["requests"]:
        cid = request["custom_id"]
        candidate = result_for(data, cid)
        if candidate:
            unit = plan["tasks"][cid]["unit"]
            units.append(unit)
            candidates[unit["id"]] = candidate
    if not units:
        raise ValueError("No validated extraction results available to review")
    return prepare(data, units, rates, plan["snapshot"], max_output_tokens, candidates, reasoning)


def export_job(data, job_id):
    job, plan = load_job(data, job_id)
    rows = []
    for request in plan["requests"]:
        cid = request["custom_id"]
        result = result_for(data, cid)
        if result:
            rows.append(
                {
                    **result,
                    "source": plan["tasks"][cid]["unit"],
                    "candidate_request_id": plan["tasks"][cid]["candidate_request_id"],
                }
            )
    write_jsonl(job / "results.jsonl", rows)
    lines = [
        f"# {plan['stage'].title()} results",
        "",
        f"Job: `{job_id}`",
        "",
        "Candidates and model reviews require human judgment before curriculum use.",
        "",
    ]
    for row in rows:
        source = row["source"]
        lines.extend(
            [
                f"## {source['source']} / {source['round']} / {source['number']}",
                "",
                f"{source['level']} · {source['kind']} · unit `{source['id']}`",
                "",
            ]
        )
        if plan["stage"] == "extract":
            for target in row["result"]["targets"]:
                lines.extend(
                    [
                        f"### {target['part']}: {target['canonical_answer']}",
                        "",
                        f"Categories: {', '.join(target['categories'])}",
                        "",
                        f"Aliases: {', '.join(target['aliases']) or '(none)'}",
                        "",
                        f"Answer notes: {target['adjudication_notes'] or '(none)'}",
                        "",
                    ]
                )
                for clue_index, clue in enumerate(target["clues"]):
                    lines.extend([f"- {clue['statement']}"])
                    for evidence in clue["evidence"]:
                        if "passage_id" in evidence:
                            span = next(
                                s
                                for s in row["evidence_spans"]
                                if s["passage_id"] == evidence["passage_id"]
                                and s["target_part"] == target["part"]
                                and s["clue_index"] == clue_index
                            )
                            evidence = {
                                "part": evidence["passage_id"].split(".")[0],
                                "field": span["field"],
                                "quote": span["quote"],
                            }
                        lines.extend(
                            [
                                f"  - Evidence ({evidence['part']}/{evidence['field']}): {evidence['quote']}"
                            ]
                        )
                lines.extend(
                    ["", f"Uncertainty: {'; '.join(target['uncertainty']) or '(none)'}", ""]
                )
        else:
            review = row["result"]
            lines.extend([f"Verdict: **{review['verdict']}**", "", review["summary"], ""])
            for dimension in ("answer_accuracy", "grounding", "clue_coverage", "context_handling"):
                lines.append(f"- {dimension}: {review[dimension]}/5")
            for issue in review["issues"]:
                lines.extend(
                    [
                        "",
                        f"- {issue['part']} / {issue['severity']} / {issue['kind']}: {issue['explanation']}",
                        f"  Suggested fix: {issue['suggested_fix']}",
                    ]
                )
            lines.append("")
        lines.extend(["### Original context", ""])
        for part in source["parts"]:
            lines.extend([f"**{part['label']}**", ""])
            lines.extend("> " + line for line in part["question"].splitlines())
            lines.extend(["", f"Answer: {part['answer'] or '(lead-in)'}", ""])
    atomic_text(job / "results.md", "\n".join(lines) + "\n")
    report = {
        "job": job_id,
        "stage": plan["stage"],
        "model": plan["rates"]["model"],
        "requested": len(plan["requests"]),
        "validated": len(rows),
        "remaining": len(plan["requests"]) - len(rows),
        "estimated_validated_usage_cost_usd": round(
            sum(r["estimated_usage_cost_usd"] for r in rows), 6
        ),
        "cost_note": "Validated results only; failed/invalid attempts can also be billed. See raw response usage and API billing.",
        "by_level_kind": dict(
            Counter(f"{r['source']['level']}/{r['source']['kind']}" for r in rows)
        ),
    }
    if plan["stage"] == "review":
        report["verdicts"] = dict(Counter(r["result"]["verdict"] for r in rows))
        report["issues"] = dict(Counter(i["kind"] for r in rows for i in r["result"]["issues"]))
        report["advisory_only"] = (
            "Model reviews are not ground truth. Human-check failures and a random sample of passes."
        )
    write_json(job / "report.json", report)
    return report


def compare(data, job_ids):
    """Compare candidates on a shared sample, including missing or invalid outputs."""
    details = []
    for job_id in job_ids:
        _, plan = load_job(data, job_id)
        if plan["stage"] != "extract":
            raise ValueError("Compare takes extraction job IDs")
        details.append((job_id, plan, export_job(data, job_id)))
    unit_sets = [{task["unit"]["id"] for task in plan["tasks"].values()} for _, plan, _ in details]
    if any(s != unit_sets[0] for s in unit_sets[1:]):
        raise ValueError("Candidate jobs must use exactly the same source units")
    reviews = {}
    for path in sorted((Path(data) / "jobs").glob("*/plan.json")):
        plan = read_json(path)
        if plan["stage"] != "review":
            continue
        for cid, task in plan["tasks"].items():
            result = result_for(data, cid)
            if result:
                reviews.setdefault(task["candidate_request_id"], {})[cid] = result
    rows = []
    for job_id, plan, summary in details:
        scores = []
        for request in plan["requests"]:
            cid = request["custom_id"]
            for review_id, result in reviews.get(cid, {}).items():
                scores.append(
                    {
                        "candidate_request_id": cid,
                        "review_request_id": review_id,
                        "reviewer": result["model_returned"],
                        "review_prompt_version": result["prompt_version"],
                        "review": result["result"],
                    }
                )
        reviewer_groups = {}
        for score in scores:
            key = f"{score['reviewer']} / {score['review_prompt_version']}"
            reviewer_groups.setdefault(key, []).append(score["review"])
        reviewer_summaries = {
            key: {
                "judgments": len(values),
                "verdicts": dict(Counter(v["verdict"] for v in values)),
                "mean_scores": {
                    dimension: round(sum(v[dimension] for v in values) / len(values), 2)
                    for dimension in (
                        "answer_accuracy",
                        "grounding",
                        "clue_coverage",
                        "context_handling",
                    )
                },
            }
            for key, values in reviewer_groups.items()
        }
        rows.append(
            {
                **summary,
                "reviewed_candidates": len({s["candidate_request_id"] for s in scores}),
                "review_verdicts": dict(Counter(s["review"]["verdict"] for s in scores)),
                "by_reviewer": reviewer_summaries,
                "reviews": scores,
            }
        )
    report = {
        "same_sample_units": len(unit_sets[0]),
        "candidates": rows,
        "note": "No automatic winner: consider validation failures, coverage, cost, and human review. Multiple reviewer judgments are retained separately.",
    }
    path = Path(data) / "comparisons" / (digest(job_ids)[:24] + ".json")
    write_json(path, report)
    return {
        "report": str(path),
        "same_sample_units": len(unit_sets[0]),
        "candidates": [{k: v for k, v in r.items() if k != "reviews"} for r in rows],
    }
