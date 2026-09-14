"""Read-only, deterministic audit of the source CSVs (standard library only)."""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {
    "tossups": ["Source", "Round", "Number", "Question", "Answer"],
    "bonuses": ["Source", "Round", "Number", "Label", "Question", "Answer"],
}


def audit():
    report, keys = {}, {}
    csv.field_size_limit(10_000_000)
    for path in sorted(ROOT.glob("*-school-*.csv")):
        kind = path.stem.rsplit("-", 1)[1]
        header = HEADERS[kind]
        rows, header_records = [], []
        with path.open(encoding="utf-8-sig", newline="") as source:
            for record, row in enumerate(csv.reader(source, strict=True), 1):
                if row == header:
                    header_records.append(record)
                    continue
                if len(row) != len(header):
                    raise ValueError(f"{path.name}: record {record}: wrong column count")
                rows.append((record, row))
        groups = defaultdict(list)
        for record, row in rows:
            groups[tuple(row[:3])].append((record, row))
        keys[path.stem] = set(groups)
        item = {
            "bytes": path.stat().st_size,
            "columns": header,
            "header_records": header_records,
            "data_rows": len(rows),
            "sources": dict(Counter(row[0] for _, row in rows)),
            "logical_keys": len(groups),
            "exact_duplicate_rows": len(rows) - len({tuple(row) for _, row in rows}),
            "repeated_text_answer_pairs": len(rows) - len({tuple(row[-2:]) for _, row in rows}),
            "missing_question_answers": [
                {"record": n, "key": row[:3], "label": row[3] if kind == "bonuses" else None}
                for n, row in rows
                if not row[-1].strip() and not (kind == "bonuses" and row[3] == "L")
            ],
        }
        if kind == "bonuses":
            item["label_sequences"] = dict(Counter("".join(r[3] for _, r in g) for g in groups.values()))
            item["invalid_bonus_groups"] = [list(k) for k, g in groups.items() if Counter(r[3] for _, r in g) != Counter("LABC")]
            item["lead_in_answer_repeats_question"] = sum(r[3] == "L" and r[4] == r[5] for _, r in rows)
        else:
            item["duplicate_keys"] = [list(k) for k, g in groups.items() if len(g) != 1]
            item["power_markers"] = sum("(*)" in r[3] for _, r in rows)
        report[path.name] = item
    for level in ("high-school", "middle-school"):
        tossups, bonuses = keys[f"{level}-tossups"], keys[f"{level}-bonuses"]
        report[f"{level}-pairing"] = {
            "tossup_keys_without_bonus": sorted(tossups - bonuses),
            "bonus_keys_without_tossup": sorted(bonuses - tossups),
        }
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, ensure_ascii=False))
