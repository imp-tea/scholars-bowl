"""Strict imports; source occurrences and complete bonus contexts are never deduplicated."""

import csv
import hashlib
import io
import random
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from .storage import digest, file_hash, read_json, read_jsonl, write_json, write_jsonl

PARSER_VERSION = "1"
HEADERS = {
    "tossup": ["Source", "Round", "Number", "Question", "Answer"],
    "bonus": ["Source", "Round", "Number", "Label", "Question", "Answer"],
}


def normalize(text):
    # Search aid only. Do not strip answer rules, annotations, or power markers.
    return " ".join(unicodedata.normalize("NFC", text).split())


def parse_dataset(root, entry):
    path = root / entry["file"]
    kind, level = entry["kind"], entry["level"]
    if kind not in HEADERS or level not in {"middle-school", "high-school"}:
        raise ValueError("Unsupported dataset kind or school level")
    header = HEADERS[kind]
    source_hash = file_hash(path)
    dataset_id = digest([entry, source_hash])
    records, header_records = [], []
    csv.field_size_limit(10_000_000)
    # Parse the very bytes whose hash is retained; detect concurrent source changes below.
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != source_hash:
        raise ValueError(f"Source changed during import: {entry['file']}")
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    for ordinal, row in enumerate(reader, 1):
        if row == header:
            header_records.append(ordinal)
            continue
        if len(row) != len(header):
            raise ValueError(f"{entry['file']}: CSV record {ordinal}: wrong column count")
        fields = dict(zip(header, row))
        if any(not fields[key].strip() for key in ("Source", "Round", "Number", "Question")):
            raise ValueError(f"{entry['file']}: CSV record {ordinal}: empty required field")
        label = fields.get("Label", "T")
        if kind == "bonus" and label not in {"L", "A", "B", "C"}:
            raise ValueError(f"{entry['file']}: CSV record {ordinal}: invalid label")
        records.append(
            {
                "id": digest([dataset_id, ordinal]),
                "dataset_id": dataset_id,
                "record": ordinal,
                "label": label,
                "raw": fields,
                "question_normalized": normalize(fields["Question"]),
                "answer_normalized": normalize(fields["Answer"]),
                "text_answer_hash": digest([fields["Question"], fields["Answer"]]),
            }
        )
    if len(header_records) != 1:
        raise ValueError(f"{entry['file']}: expected exactly one schema header")
    return {
        **entry,
        "id": dataset_id,
        "sha256": source_hash,
        "headers": header_records,
        "rows": len(records),
    }, records


def ingest(root, data):
    root, data = Path(root), Path(data)
    manifest = read_json(root / "datasets.json")
    if manifest.get("version") != 1:
        raise ValueError("Unsupported dataset manifest version")
    entries = manifest["datasets"]
    if len({x["file"] for x in entries}) != len(entries):
        raise ValueError("Duplicate file in dataset manifest")
    datasets, records, units, anomalies = [], [], [], []
    for entry in entries:
        dataset, rows = parse_dataset(root, entry)
        datasets.append(dataset)
        records.extend(rows)
        groups = defaultdict(list)
        for row in rows:
            groups[tuple(row["raw"][x] for x in ("Source", "Round", "Number"))].append(row)
        for key, group in groups.items():
            valid = True
            if entry["kind"] == "bonus":
                valid = Counter(r["label"] for r in group) == Counter("LABC")
                if not valid:
                    anomalies.append(
                        {"type": "invalid_bonus_labels", "level": entry["level"], "key": key}
                    )
                group = sorted(group, key=lambda r: "LABC".index(r["label"]))
                chunks = [group]
            else:
                if len(group) > 1:
                    anomalies.append(
                        {"type": "duplicate_tossup_key", "level": entry["level"], "key": key}
                    )
                chunks = [[r] for r in group]
            for chunk in chunks:
                parts = []
                eligible = valid
                for row in chunk:
                    fields = row["raw"]
                    if row["label"] != "L" and not fields["Answer"].strip():
                        eligible = False
                        anomalies.append(
                            {"type": "missing_answer", "record_id": row["id"], "key": key}
                        )
                    if row["label"] == "L" and fields["Answer"]:
                        anomalies.append(
                            {"type": "lead_in_answer_ignored", "record_id": row["id"], "key": key}
                        )
                    parts.append(
                        {
                            "label": row["label"],
                            "record_id": row["id"],
                            "question": fields["Question"],
                            "answer": "" if row["label"] == "L" else fields["Answer"],
                        }
                    )
                units.append(
                    {
                        "id": digest([PARSER_VERSION, dataset["id"], [r["id"] for r in chunk]]),
                        "dataset_id": dataset["id"],
                        "level": entry["level"],
                        "kind": entry["kind"],
                        "source": key[0],
                        "round": key[1],
                        "number": key[2],
                        "eligible": eligible,
                        "parts": parts,
                        "paired_unit_ids": [],
                    }
                )
    pairs = defaultdict(lambda: defaultdict(list))
    for unit in units:
        pairs[(unit["level"], unit["source"], unit["round"], unit["number"])][unit["kind"]].append(
            unit
        )
    for key, kinds in pairs.items():
        for kind, other in (("tossup", "bonus"), ("bonus", "tossup")):
            for unit in kinds[kind]:
                unit["paired_unit_ids"] = [x["id"] for x in kinds[other]]
        if not kinds["bonus"] or not kinds["tossup"]:
            anomalies.append(
                {"type": "missing_bonus" if not kinds["bonus"] else "missing_tossup", "key": key}
            )
        elif len(kinds["tossup"]) != 1 or len(kinds["bonus"]) != 1:
            anomalies.append({"type": "ambiguous_pair", "key": key})
    snapshot_id = digest([PARSER_VERSION, datasets])[:24]
    directory = data / "corpus" / snapshot_id
    duplicate_counts = Counter(r["text_answer_hash"] for r in records)
    report = {
        "snapshot": snapshot_id,
        "parser_version": PARSER_VERSION,
        "datasets": datasets,
        "raw_records": len(records),
        "units": len(units),
        "eligible_units": sum(u["eligible"] for u in units),
        "counts": dict(Counter(f"{u['level']}/{u['kind']}" for u in units)),
        "repeated_text_answer_occurrences": sum(n - 1 for n in duplicate_counts.values()),
        "anomalies": anomalies,
    }
    directory.mkdir(parents=True, exist_ok=True)
    # Snapshot completion is the final manifest write; incomplete imports can be rerun.
    write_jsonl(directory / "records.jsonl", records)
    write_jsonl(directory / "units.jsonl", units)
    report["artifact_hashes"] = {
        name: file_hash(directory / name) for name in ("records.jsonl", "units.jsonl")
    }
    write_json(directory / "manifest.json", report)
    write_json(data / "corpus" / "current.json", {"snapshot": snapshot_id})
    return report


def load_corpus(data):
    current = read_json(Path(data) / "corpus" / "current.json")["snapshot"]
    directory = Path(data) / "corpus" / current
    manifest = read_json(directory / "manifest.json")
    if not manifest.get("artifact_hashes"):
        raise ValueError("Corpus snapshot needs an integrity manifest; run qb ingest")
    if any(
        file_hash(directory / name) != checksum
        for name, checksum in manifest["artifact_hashes"].items()
    ):
        raise ValueError("Corpus snapshot was modified; rerun qb ingest to restore it")
    return manifest, list(read_jsonl(directory / "units.jsonl"))


def select_units(units, limit=36, seed=42):
    """Round-robin random sample over level × kind × tournament; same IDs for every model."""
    groups = defaultdict(list)
    for unit in sorted(units, key=lambda u: u["id"]):
        if unit["eligible"]:
            groups[(unit["level"], unit["kind"], unit["source"])].append(unit)
    rng = random.Random(seed)
    keys = sorted(groups)
    for key in keys:
        rng.shuffle(groups[key])
    rng.shuffle(keys)
    selected = []
    while keys and (limit is None or len(selected) < limit):
        next_keys = []
        for key in keys:
            if limit is not None and len(selected) >= limit:
                break
            selected.append(groups[key].pop())
            if groups[key]:
                next_keys.append(key)
        keys = next_keys
    return selected
