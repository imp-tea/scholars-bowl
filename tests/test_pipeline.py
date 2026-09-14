import copy
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scholars_bowl.corpus import ingest, load_corpus, parse_dataset, select_units
from scholars_bowl.extraction import passages, review_schema, validate_extraction
from scholars_bowl.jobs import (
    accept_result,
    compare,
    import_results,
    load_job,
    prepare,
    prepare_review,
    recover,
    retry_job,
    run_sync,
    safe_api_error,
    submit,
)
from scholars_bowl.pricing import PROFILES
from scholars_bowl.storage import file_hash, read_json, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def unit():
    return {
        "id": "unit1",
        "kind": "tossup",
        "level": "middle-school",
        "source": "Test 2020",
        "round": "1",
        "number": "1",
        "eligible": True,
        "parts": [
            {
                "label": "T",
                "record_id": "record1",
                "question": "Mary Shelley wrote this novel.",
                "answer": "Frankenstein",
            }
        ],
    }


@pytest.fixture
def extraction():
    return {
        "targets": [
            {
                "part": "T",
                "canonical_answer": "Frankenstein",
                "answer_kind": "entity",
                "aliases": [],
                "adjudication_notes": "",
                "categories": ["literature"],
                "clues": [
                    {
                        "statement": "Written by Mary Shelley",
                        "evidence": [
                            {
                                "passage_id": "T.q0",
                            }
                        ],
                    }
                ],
                "uncertainty": [],
            }
        ]
    }


def body(value):
    return {
        "status": "completed",
        "id": "resp_test",
        "model": "test",
        "usage": {"input_tokens": 100, "output_tokens": 100},
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}
        ],
    }


def test_full_corpus_read_only_and_idempotent(tmp_path):
    hashes = {p: file_hash(p) for p in ROOT.glob("*.csv")}
    report = ingest(ROOT, tmp_path)
    assert report["raw_records"] == 10956
    assert report["units"] == report["eligible_units"] == 4383
    assert report["counts"] == {
        "high-school/tossup": 1532,
        "high-school/bonus": 1531,
        "middle-school/tossup": 660,
        "middle-school/bonus": 660,
    }
    assert report["anomalies"] == [
        {"type": "missing_bonus", "key": ("high-school", "2020 TAILS", "10", "20")}
    ]
    assert ingest(ROOT, tmp_path) == report
    _, units = load_corpus(tmp_path)
    assert len({u["id"] for u in units}) == 4383
    assert len({(u["level"], u["kind"], u["source"]) for u in select_units(units, 36)}) == 18
    assert select_units(units, 36) == select_units(list(reversed(units)), 36)
    assert all(
        [p["label"] for p in u["parts"]] == list("LABC") for u in units if u["kind"] == "bonus"
    )
    assert hashes == {p: file_hash(p) for p in hashes}
    for unit in units:
        for passage in passages(unit).values():
            part = next(p for p in unit["parts"] if p["label"] == passage["part"])
            assert part[passage["field"]][passage["start"] : passage["end"]] == passage["text"]


def test_csv_header_at_end_unicode_newline_and_raw_lead_in(tmp_path):
    header = ["Source", "Round", "Number", "Label", "Question", "Answer"]
    rows = [
        [
            "Source with , comma",
            "1",
            "2",
            label,
            "Clue “é”\nnext line",
            "Clue “é”\nnext line" if label == "L" else "answer",
        ]
        for label in "ABCL"
    ]
    with (tmp_path / "bonus.csv").open("w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(rows + [header])
    entry = {"file": "bonus.csv", "level": "middle-school", "kind": "bonus"}
    dataset, records = parse_dataset(tmp_path, entry)
    assert dataset["headers"] == [5]
    assert [r["record"] for r in records] == [1, 2, 3, 4]
    assert records[-1]["raw"]["Answer"] == "Clue “é”\nnext line"
    write_json(tmp_path / "datasets.json", {"version": 1, "datasets": [entry]})
    ingest(tmp_path, tmp_path / "data")
    _, units = load_corpus(tmp_path / "data")
    assert units[0]["parts"][0]["label"] == "L"
    assert units[0]["parts"][0]["answer"] == ""


def test_malformed_csv_not_silently_skipped(tmp_path):
    (tmp_path / "bad.csv").write_text("Source,Round,Number,Question,Answer\na,1,1,missing\n")
    with pytest.raises(ValueError, match="column count"):
        parse_dataset(tmp_path, {"file": "bad.csv", "level": "high-school", "kind": "tossup"})


def test_duplicate_natural_keys_and_missing_parts_preserved(tmp_path):
    (tmp_path / "t.csv").write_text("Source,Round,Number,Question,Answer\na,1,1,q,a\na,1,1,q,b\n")
    (tmp_path / "b.csv").write_text(
        "Source,Round,Number,Label,Question,Answer\na,1,1,L,lead,\na,1,1,A,q,\n"
    )
    write_json(
        tmp_path / "datasets.json",
        {
            "version": 1,
            "datasets": [
                {"file": "t.csv", "level": "high-school", "kind": "tossup"},
                {"file": "b.csv", "level": "high-school", "kind": "bonus"},
            ],
        },
    )
    report = ingest(tmp_path, tmp_path / "data")
    assert report["raw_records"] == 4
    assert report["units"] == 3
    assert {a["type"] for a in report["anomalies"]} == {
        "duplicate_tossup_key",
        "invalid_bonus_labels",
        "missing_answer",
        "ambiguous_pair",
    }
    assert report["eligible_units"] == 2


def test_evidence_validation(unit, extraction):
    _, spans = validate_extraction(extraction, unit)
    assert spans[0]["record_id"] == "record1"
    assert spans[0]["positions"] == [{"start": 0, "end": 30}]
    extraction["targets"][0]["clues"][0]["evidence"][0]["passage_id"] = "T.q99"
    with pytest.raises(ValueError, match="unknown passage"):
        validate_extraction(extraction, unit)


def test_context_and_target_coverage(unit, extraction):
    unit["kind"] = "bonus"
    unit["parts"] = [{**unit["parts"][0], "label": x, "record_id": x} for x in "LABC"]
    extraction["targets"] = [{**copy.deepcopy(extraction["targets"][0]), "part": x} for x in "ABC"]
    for t in extraction["targets"]:
        t["clues"][0]["evidence"][0]["passage_id"] = "L.q0"
    validate_extraction(extraction, unit)
    extraction["targets"][0]["clues"][0]["evidence"][0]["passage_id"] = "C.q0"
    with pytest.raises(ValueError, match="later"):
        validate_extraction(extraction, unit)
    extraction["targets"] = extraction["targets"][:1]
    with pytest.raises(ValueError, match="coverage"):
        validate_extraction(extraction, unit)


def test_job_identity_covers_model_prompt_source_and_limits(tmp_path, unit):
    a, _ = prepare(tmp_path, [unit], PROFILES["nano"], "snapshot")
    assert prepare(tmp_path, [unit], PROFILES["nano"], "snapshot")[0] == a
    assert prepare(tmp_path, [unit], PROFILES["mini"], "snapshot")[0] != a
    assert prepare(tmp_path, [unit], PROFILES["nano"], "snapshot", 5000)[0] != a
    other = {**unit, "level": "high-school", "id": "unit2"}
    assert prepare(tmp_path, [other], PROFILES["nano"], "snapshot")[0] != a


def test_unordered_partial_results_and_retry(tmp_path, unit, extraction):
    second = {**unit, "id": "unit2"}
    job_id, _ = prepare(tmp_path, [unit, second], PROFILES["nano"], "snapshot")
    job, plan = load_job(tmp_path, job_id)
    ids = list(plan["tasks"])
    write_json(job / "remote.json", {"custom_ids": ids})
    write_json(job / "batch-status.json", {"status": "expired"})
    write_jsonl(
        job / "batch-output.jsonl",
        [{"custom_id": ids[1], "response": {"status_code": 200, "body": body(extraction)}}],
    )
    result = import_results(tmp_path, job_id)
    assert result["validated"] == 1
    assert result["errors"] == [{"custom_id": ids[0], "error": "No result returned"}]
    assert import_results(tmp_path, job_id) == result
    retried = retry_job(tmp_path, job_id)
    assert retried["job"] != job_id and retried["requests"] == 1
    _, new_plan = load_job(tmp_path, retried["job"])
    assert new_plan["requests"][0]["custom_id"] == ids[0]


@pytest.mark.parametrize("change", ["incomplete", "refusal", "bad_quote"])
def test_invalid_responses_not_cached(tmp_path, unit, extraction, change):
    job_id, _ = prepare(tmp_path, [unit], PROFILES["nano"], "snapshot")
    _, plan = load_job(tmp_path, job_id)
    response = body(extraction)
    if change == "incomplete":
        response["status"] = "incomplete"
    elif change == "refusal":
        response["output"][0]["content"] = [{"type": "refusal", "refusal": "No"}]
    else:
        extraction["targets"][0]["clues"][0]["evidence"][0]["passage_id"] = "T.q99"
        response = body(extraction)
    with pytest.raises(ValueError):
        accept_result(tmp_path, plan, plan["requests"][0]["custom_id"], response, True)
    assert not (tmp_path / "cache").exists()


def test_foreign_output_rejected_before_caching(tmp_path, unit, extraction):
    job_id, _ = prepare(tmp_path, [unit], PROFILES["nano"], "s")
    job, plan = load_job(tmp_path, job_id)
    cid = plan["requests"][0]["custom_id"]
    write_json(job / "remote.json", {"custom_ids": [cid]})
    row = {"custom_id": cid, "response": {"status_code": 200, "body": body(extraction)}}
    write_jsonl(job / "batch-output.jsonl", [row, {**row, "custom_id": "foreign"}])
    with pytest.raises(ValueError, match="Unexpected"):
        import_results(tmp_path, job_id)
    assert not (tmp_path / "cache").exists()


class Batch:
    id = "batch_test"
    status = "validating"

    def model_dump(self, **kwargs):
        return {"id": self.id, "status": self.status}


def test_submit_resume_no_duplicate_and_budget(tmp_path, unit):
    job_id, _ = prepare(tmp_path, [unit], PROFILES["nano"], "s")
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return Batch()

    client = SimpleNamespace(
        files=SimpleNamespace(create=lambda **kw: SimpleNamespace(id="file_test")),
        batches=SimpleNamespace(create=create),
    )
    with pytest.raises(ValueError, match="exceeds"):
        submit(tmp_path, tmp_path, job_id, 0.000001, client)
    assert not calls
    assert not (tmp_path / "jobs" / job_id / "remote.json").exists()
    assert submit(tmp_path, tmp_path, job_id, 1, client)["batch_id"] == "batch_test"
    assert submit(tmp_path, tmp_path, job_id, 1, client)["already_submitted"]
    assert len(calls) == 1


def test_uncertain_submission_requires_recovery(tmp_path, unit):
    job_id, _ = prepare(tmp_path, [unit], PROFILES["nano"], "s")

    def crash(**kw):
        raise RuntimeError("Simulated connection lost after server accepted")

    client = SimpleNamespace(
        files=SimpleNamespace(create=lambda **kw: SimpleNamespace(id="file_test")),
        batches=SimpleNamespace(create=crash),
    )
    with pytest.raises(RuntimeError):
        submit(tmp_path, tmp_path, job_id, 1, client)
    with pytest.raises(ValueError, match="uncertain"):
        submit(tmp_path, tmp_path, job_id, 1, client)
    remote = read_json(tmp_path / "jobs" / job_id / "remote.json")
    batch = SimpleNamespace(
        id="found",
        input_file_id="file_test",
        metadata={"qb_job": job_id, "qb_submission": remote["submission_tag"]},
    )
    client.batches.list = lambda **kw: [batch]
    assert recover(tmp_path, tmp_path, job_id, client=client)["batch_id"] == "found"


def test_sync_cache_and_blinded_review(tmp_path, unit, extraction):
    job_id, _ = prepare(tmp_path, [unit], PROFILES["nano"], "s")
    calls = []

    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(model_dump=lambda **kw: body(extraction))

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    assert run_sync(tmp_path, tmp_path, job_id, 1, 1, client)["valid_total"] == 1
    assert run_sync(tmp_path, tmp_path, job_id, 1, 1, client)["attempted"] == 0
    assert len(calls) == 1
    review_id, _ = prepare_review(tmp_path, job_id, PROFILES["reviewer"])
    _, review = load_job(tmp_path, review_id)
    assert "gpt-4.1-nano" not in review["requests"][0]["body"]["input"]
    assert review["tasks"][review["requests"][0]["custom_id"]]["candidate_request_id"]
    other, _ = prepare(tmp_path, [{**unit, "id": "other"}], PROFILES["mini"], "s")
    with pytest.raises(ValueError, match="same source units"):
        compare(tmp_path, [job_id, other])


def test_overlapping_batch_jobs_are_blocked(tmp_path, unit):
    original, _ = prepare(tmp_path, [unit], PROFILES["nano"], "s")
    expanded, _ = prepare(tmp_path, [unit, {**unit, "id": "second"}], PROFILES["nano"], "s")
    client = SimpleNamespace(
        files=SimpleNamespace(create=lambda **kw: SimpleNamespace(id="file_test")),
        batches=SimpleNamespace(create=lambda **kw: Batch()),
    )
    submit(tmp_path, tmp_path, original, 1, client)
    with pytest.raises(ValueError, match="Overlapping"):
        submit(tmp_path, tmp_path, expanded, 1, client)


def test_corpus_integrity_manifest(tmp_path):
    report = ingest(ROOT, tmp_path)
    directory = tmp_path / "corpus" / report["snapshot"]
    with (directory / "units.jsonl").open("a") as f:
        f.write("\n")
    with pytest.raises(ValueError, match="modified"):
        load_corpus(tmp_path)


@pytest.mark.parametrize("version", ["extract-v2-passages", "extract-v3-explicit-aliases"])
def test_passage_prompt_revision_preserves_saved_outputs(unit, extraction, version):
    old_result, old_spans = validate_extraction(extraction, unit, version)
    result, spans = validate_extraction(extraction, unit)
    assert (result, spans) == (old_result, old_spans)


def test_legacy_quote_outputs_remain_readable(unit):
    value = {
        "targets": [
            {
                "part": "T",
                "canonical_answer": "Frankenstein",
                "answer_kind": "entity",
                "aliases": [],
                "adjudication_notes": "",
                "categories": ["literature"],
                "clues": [
                    {
                        "statement": "Written by Mary Shelley",
                        "evidence": [{"part": "T", "field": "question", "quote": "Mary Shelley"}],
                    }
                ],
                "uncertainty": [],
            }
        ]
    }
    _, spans = validate_extraction(value, unit, "extract-v1")
    assert spans[0]["quote"] == "Mary Shelley"


def test_cost_thresholds_reject_nonfinite_values(tmp_path, unit):
    job_id, _ = prepare(tmp_path, [unit], PROFILES["nano"], "s")
    with pytest.raises(ValueError, match="exceeds"):
        submit(tmp_path, tmp_path, job_id, float("nan"))


def test_reviewer_schema_restricts_issue_labels_to_source_targets(unit):
    assert review_schema(unit)["$defs"]["ReviewIssue"]["properties"]["part"]["enum"] == ["T"]
    unit["parts"] = [{**unit["parts"][0], "label": label} for label in "LABC"]
    assert review_schema(unit)["$defs"]["ReviewIssue"]["properties"]["part"]["enum"] == list("ABC")


def test_api_error_redacts_provider_message():
    class ProviderError(Exception):
        status_code = 401

    message = safe_api_error(ProviderError("Incorrect API key provided: sk-example-secret"))
    assert "sk-example-secret" not in message
    assert "401" in message


@pytest.mark.parametrize("workers", [1, 4])
def test_synchronous_pilot_supports_full_sample(tmp_path, unit, extraction, workers):
    units = [{**unit, "id": f"unit-{i}"} for i in range(36)]
    job_id, budget = prepare(tmp_path, units, PROFILES["mini"], "s")
    assert budget["batch"] is False
    _, plan = load_job(tmp_path, job_id)
    assert plan["requests"][0]["body"]["reasoning"] == {"effort": "low"}
    client = SimpleNamespace(
        responses=SimpleNamespace(
            create=lambda **kw: SimpleNamespace(model_dump=lambda **kw: body(extraction))
        )
    )
    result = run_sync(tmp_path, tmp_path, job_id, 36, 1, client, workers=workers)
    assert result["valid_total"] == 36
    assert not (tmp_path / "jobs" / job_id / "remote.json").exists()


def test_parallel_pilot_checkpoints_inflight_success_on_error(
    tmp_path, unit, extraction, monkeypatch
):
    from concurrent.futures import wait
    from threading import Barrier, Lock

    units = [{**unit, "id": f"unit-{i}"} for i in range(8)]
    job_id, _ = prepare(tmp_path, units, PROFILES["mini"], "s")
    barrier, lock = Barrier(2), Lock()
    calls = []

    def create(**kwargs):
        with lock:
            index = len(calls)
            calls.append(index)
        barrier.wait(timeout=5)
        if index == 0:
            raise RuntimeError("provider unavailable")
        return SimpleNamespace(model_dump=lambda **kw: body(extraction))

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    # Deliver both completed futures together to make the failure observation deterministic.
    monkeypatch.setattr("scholars_bowl.jobs.wait", lambda futures, **kw: wait(futures))
    with pytest.raises(RuntimeError, match="provider unavailable"):
        run_sync(tmp_path, tmp_path, job_id, 8, 1, client, workers=2)
    assert len(calls) == 2
    assert len(list((tmp_path / "cache").glob("*.json"))) == 1
    assert len(list((tmp_path / "jobs" / job_id / "sync").glob("*.json"))) == 1
