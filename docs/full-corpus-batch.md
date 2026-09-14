# Full-corpus Batch preparation

**Prepared locally; not uploaded or submitted.** The user selected Luna with medium reasoning and explicitly requested preparation only. Do not execute submission commands until the user authorizes starting.

## Configuration

- Model: `gpt-5.6-luna`; reasoning: `medium`. This is now the CLI extraction default.
- Prompt: `extract-v4-no-conditional-aliases`. Added exactly: “Do not include conditionally accepted answers in aliases.” Other extraction instructions and schema are unchanged.
- Output limit: 8,000 tokens per request, including reasoning, matching the Luna pilot.
- Endpoint: `/v1/responses`; planned Batch completion window: `24h`.
- Snapshot: `00d37fc5066b7356e83c2d0b`.
- Full coverage: 4,383 unique source units: 2,192 tossups and 2,191 complete bonus sets, representing 8,765 answer targets. School levels and source provenance remain attached; repeated source occurrences remain separate.
- Four disjoint jobs separate school level and question kind. Bonuses retain L/A/B/C together. The missing high-school bonus at `2020 TAILS / 10 / 20` remains flagged; its tossup is included.

## Prepared jobs

| Level / kind | Requests | Request file MB | Pilot-based Batch projection | Estimate at output cap | Job ID |
| --- | ---: | ---: | ---: | ---: | --- |
| middle-school / tossup | 660 | 3.36 | $0.21 | $3.27 | `dd628ff9770f15581b29759c` |
| middle-school / bonus | 660 | 3.78 | $0.45 | $3.28 | `70dd847903fefe682fa1fdaf` |
| high-school / tossup | 1,532 | 8.07 | $0.54 | $7.59 | `fc2d4303c398c9019fcfe577` |
| high-school / bonus | 1,531 | 8.87 | $0.98 | $7.61 | `cccb4ee6de4555393b0b6c57` |

**Projected extraction cost: about $2.19.** This extrapolates the 36-unit Luna pilot separately within each level/kind group and applies the Batch discount. The pilot used v3; this preparation uses the requested v4 sentence. It is an estimate, not a ceiling.

**Conservative estimate at the output-token limits: $21.74.** This assumes every response uses all 8,000 output tokens, plus padded input estimates. The per-job `--max-cost` values below cover this estimate, totaling $22.50; they are planning checks, not API-enforced spending limits. Both estimates exclude separate reviews and retries.

Each `data/jobs/JOB_ID/` contains an immutable `plan.json` and a Batch-format `requests.jsonl` with unique custom IDs. `submit` will generate its upload input from still-pending requests when explicitly run. Preparation did not create `remote.json`, upload files, generate responses, or create remote batch IDs.

Machine-readable preparation manifest: `data/production/luna-v4-preparation.json`. It records counts, file hashes, settings, budgets, and all job IDs. Generated data is Git-ignored; preserve the files to retain this preparation.

## Verification

- Re-imported source CSVs read-only; corpus snapshot and counts are unchanged.
- Confirmed exact coverage of all 4,383 source IDs with no overlap or omission across the four jobs.
- Verified every request uses Luna, medium reasoning, the new instruction, an 8,000-token cap, and the correct complete source payload.
- Re-read all serialized request files and checked immutable-plan hashes. Each file is under 9 MB and each job under 1,600 requests.
- No requests are already cached under this new prompt version or overlap with an outstanding older Batch request.
- All 26 offline tests, lint, and formatting checks passed, including compatibility with saved v2/v3 passage outputs. No live model test was run in this preparation step.

## When the user authorizes starting

Run one job at a time initially. OpenAI limits queued prompt tokens per model across active batches; the account-specific remaining queue allowance has not been checked here. Splitting into four jobs avoids putting all ~7.04 million estimated prompt tokens into one batch. Each prepared job is below the public 50,000-request and 200 MB file limits. See [OpenAI Batch limits](https://developers.openai.com/api/docs/guides/batch).

The commands below are recorded for later use; they have **not** been executed. From the repository root, use the matching job and budget:

| Job | Submit command after authorization |
| --- | --- |
| middle-school tossup | `.venv/bin/qb submit dd628ff9770f15581b29759c --max-cost 3.50` |
| middle-school bonus | `.venv/bin/qb submit 70dd847903fefe682fa1fdaf --max-cost 3.50` |
| high-school tossup | `.venv/bin/qb submit fc2d4303c398c9019fcfe577 --max-cost 7.75` |
| high-school bonus | `.venv/bin/qb submit cccb4ee6de4555393b0b6c57 --max-cost 7.75` |

After each submission:

```bash
.venv/bin/qb status JOB_ID
.venv/bin/qb collect JOB_ID
.venv/bin/qb report JOB_ID
```

Wait for a terminal state and collect results before moving on or retrying failures. If submission is uncertain, use `qb recover JOB_ID`; do not blindly resubmit. Re-running `submit` after a known successful submission returns the existing Batch ID. Inspect validation failures and quality samples after collection; this operation produces source-level extraction candidates, not a resolved topic database or automatically approved curriculum.

## Recreate locally without API calls

These commands reproduce the four plans from the current source snapshot and current code:

```bash
.venv/bin/qb prepare --profile luna --reasoning medium --max-output-tokens 8000 --all --level middle-school --kind tossup --seed 42
.venv/bin/qb prepare --profile luna --reasoning medium --max-output-tokens 8000 --all --level middle-school --kind bonus --seed 42
.venv/bin/qb prepare --profile luna --reasoning medium --max-output-tokens 8000 --all --level high-school --kind tossup --seed 42
.venv/bin/qb prepare --profile luna --reasoning medium --max-output-tokens 8000 --all --level high-school --kind bonus --seed 42
```

The generic `prepare` command prints standard synchronous pricing; the preparation manifest above calculates Batch pricing explicitly. Changing source files, prompt, schema, model, or request settings creates new job IDs; do not edit these saved plans.
