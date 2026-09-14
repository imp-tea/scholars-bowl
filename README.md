# Scholars Bowl processing CLI

Python scripts for importing the question corpus, extracting source-backed answer topics and recognition clues, and comparing inexpensive models before processing everything. Runs from your terminal without Codex or a running application server.

## Setup

Requires Python 3.11 or newer. From this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
qb --help
qb doctor --online
```

The CLI reads `OPENAI_API_KEY` from your shell environment, or from this project's `.env`. The existing `.env` is already configured and ignored by Git. The key is never placed in requests files or logs. `doctor --online` checks authentication and baseline model access without generating model output.

From another directory, use `qb --root /path/to/scholars-bowl COMMAND`. Global options such as `--root` and `--data-dir` go before the command. `python -m scholars_bowl` is equivalent to `qb`.

## Import and prepare a trial

```bash
qb ingest
qb corpus
qb prepare --profile nano --limit 36 --seed 42
qb prepare --profile mini --limit 36 --seed 42
qb prepare --profile luna --reasoning medium --limit 36 --seed 42
qb jobs
```

`ingest` reads the full corpus into a versioned snapshot: currently 2,192 tossups and 2,191 complete bonus sets. Source CSVs stay untouched. Each bonus is one extraction request containing L/A/B/C in order. The known missing bonus remains in the anomaly report; its tossup is still independently usable.

`prepare` creates a local job and prints its ID, directory, and estimated synchronous cost. It makes no OpenAI requests. The default sample includes two units per tournament/question-kind combination, covering both school levels. Both profiles receive the same sample. Categories are not yet verified, so this is tournament-balanced, not category-stratified. Increasing `--limit` extends the same deterministic sample order.

Inspect `data/jobs/JOB_ID/requests.jsonl` and `plan.json`. The plan records the complete request, prompt/schema version, source context, and prices. Never edit a saved plan; change code/options and prepare a new job.

## Run, collect, and inspect

Replace `JOB_ID` in these examples with the ID printed by `prepare`:

```bash
# Optional: up to two pending requests at standard API prices for fast feedback.
qb smoke JOB_ID --limit 2 --max-cost 0.10

# Run the rest of the pilot synchronously.
qb run JOB_ID --limit 36 --workers 4 --max-cost 1.00
qb report JOB_ID
```

Only `smoke`, `run`, and `submit` incur generation charges. All testing, including model reviews, uses synchronous `run`/`smoke`; reserve `submit` (Batch) for large-scale processing. A smoke command processes up to the requested number of still-unvalidated units; another invocation can advance to more units. Successful smoke results are cached and omitted from the later Batch submission.

Batch jobs run remotely after the command exits. Check and collect later; no terminal needs to stay open. Terminal batches with partial successes are collected too. Results are matched by request ID, not output order. [OpenAI Batch guide](https://developers.openai.com/api/docs/guides/batch)

`report` writes source-linked `results.jsonl`, readable `results.md`, and summary `report.json` inside the job directory. Extracted answers and clues are **candidates**, not a published curriculum or a resolved cross-corpus topic database. Models select numbered source passages; Python attaches the verbatim source text, raw-record IDs, and character offsets. Passage IDs and bonus-part dependencies are validated. Schema validation and quote matching cannot prove that a statement follows from its evidence.

## Larger-model review and comparison

```bash
qb review NANO_JOB_ID
qb review MINI_JOB_ID
# Each command prints a new review job ID.
qb run REVIEW_JOB_ID --limit 36 --workers 4 --max-cost 4.00
qb report REVIEW_JOB_ID
qb compare NANO_JOB_ID MINI_JOB_ID
```

Review defaults to a 6,000-token output cap (including reasoning). The reviewer receives the source unit and candidate extraction with the candidate model name hidden. It checks answer identity, aliases, grounding, coverage of distinctive clues, and bonus context. It scores those dimensions and gives actionable pass/revise/reject feedback. Reviews never automatically overwrite extractions.

`review` includes all currently validated candidates from its parent job. If only smoke results exist, it creates a partial review; rerun after collection to prepare reviews for the enlarged set. Already validated identical review requests reuse the cache. Collect earlier reviews before submitting an overlapping job.

`compare` requires identical source-unit selections and counts validation failures and unreviewed candidates, alongside all available reviewer judgments. Reports are written to `data/comparisons/`. Human-check major issues and a random sample of passes: larger-model approval is not ground truth. Use a broader held-out sample covering difficult answer rules and bonus dependencies before selecting a production model.

## Models and cost controls

The nano and mini extraction profiles use pinned GPT-5 snapshots with low reasoning and an 8,000-token output cap, including reasoning. The luna profile uses `gpt-5.6-luna` with medium reasoning and the same output cap. GPT-4.1 remains available through baseline profiles. The default reviewer is GPT-5.4 with low reasoning, which caught problems missed by GPT-4.1 in the initial trial. These are test candidates, not a finalized production selection.

| Profile | Model | Standard input/output USD per 1M tokens | Batch input/output |
| --- | --- | --- | --- |
| nano | gpt-5-nano-2025-08-07 | 0.05 / 0.40 | 0.025 / 0.20 |
| nano-baseline | gpt-4.1-nano-2025-04-14 | 0.10 / 0.40 | 0.05 / 0.20 |
| mini | gpt-5-mini-2025-08-07 | 0.25 / 2.00 | 0.125 / 1.00 |
| mini-baseline | gpt-4.1-mini-2025-04-14 | 0.40 / 1.60 | 0.20 / 0.80 |
| luna | gpt-5.6-luna | 0.20 / 1.20 | 0.10 / 0.60 |
| reviewer | gpt-5.4-2026-03-05 | 2.50 / 15.00 | 1.25 / 7.50 |
| reviewer-baseline | gpt-4.1-2025-04-14 | 2.00 / 8.00 | 1.00 / 4.00 |

Prices checked 2026-09-14 against [OpenAI pricing](https://developers.openai.com/api/docs/pricing). Availability and rates can change. Actual returned model IDs and token usage are saved.

Luna's model ID, medium reasoning support, and standard rates were also verified against its [model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna). Its requested ID is not a dated snapshot; saved responses record the model returned by the API.

To test another Responses/Structured Outputs-compatible model, pass `--model MODEL_ID --input-rate RATE --output-rate RATE`. Rates are **standard** USD per million; Batch estimates apply the discount. For supported reasoning models, also use `--reasoning low` and allow enough `--max-output-tokens` for reasoning plus visible output. Model access and parameter compatibility must be tested before a large submission.

`--max-cost` checks a padded tokenizer estimate plus the full output-token cap before uploading/submitting. It is a planning threshold, **not an API-enforced dollar ceiling**. Reports estimate cost from returned usage; invalid/failed responses may also be billed and are excluded from the validated-result total. API billing is authoritative. Cached-token discounts are conservatively ignored.

## Resume and scale

```bash
# Prepare only unvalidated requests, then retry a pilot synchronously.
qb retry JOB_ID
qb run NEW_RETRY_JOB_ID --limit 36 --max-cost 1.00

# If the submission response was lost, recover it without submitting again.
qb recover JOB_ID
# Or identify the matching batch from the API dashboard:
qb recover JOB_ID --batch-id BATCH_ID

# After evaluating quality, prepare larger independent slices.
qb prepare --profile luna --limit 250 --offset 0
qb prepare --profile luna --limit 250 --offset 250
# Or prepare the whole corpus; preparation itself does not submit anything.
qb prepare --profile luna --all
# For large-scale work only, submit the prepared job through Batch:
qb submit LARGE_JOB_ID --max-cost YOUR_ESTIMATED_BUDGET
qb status LARGE_JOB_ID
qb collect LARGE_JOB_ID
```

Successful requests are cached by source identity plus full request/prompt/schema/model settings. Repeating `submit` on an already submitted job returns its Batch ID. Locks prevent concurrent mutation, and overlapping outstanding Batch requests are blocked. An uncertain create operation stays blocked until `recover` locates it; no blind create retries occur. A failed upload can leave an unused remote input file, but it cannot by itself create a paid generation job.

Raw outputs, validation failures, and missing results remain inspectable. `retry` keeps the same requests; for persistent schema/quality failures, fix the prompt/model and prepare a new job instead. Remote batch error details are retained in local artifacts, while console API errors are redacted to avoid echoing credentials.

## Files and development

- `datasets.json`: explicit filename → school level/question kind mapping.
- `src/scholars_bowl/`: importer, extraction/review contracts, pricing, job lifecycle, CLI.
- `tests/`: full-corpus invariants and mocked API lifecycle tests; no paid calls.
- `data/corpus/SNAPSHOT/`: raw records, contextual units, manifest/anomalies.
- `data/jobs/JOB_ID/`: immutable plan, request JSONL, remote IDs, outputs, reports.
- `data/cache/`: validated extraction/review results. Back up `data/` to preserve paid work.
- `data/` and `.venv/` are generated and ignored. Input CSVs, code, tests, and docs are tracked.

```bash
python -m pytest -q
ruff check src tests
ruff format --check src tests
python scripts/inspect_corpus.py
```

The initial implementation stops at validated, reviewed source-level candidates. Cross-corpus entity resolution, explicit relationship extraction, human corrections, topic aggregation with level membership, importance scoring, study summaries, and the training UI are subsequent phases. Repeated source occurrences are preserved for that work.

The initial live trial and exact job IDs are recorded in [docs/pipeline-pilot.md](docs/pipeline-pilot.md).

`--workers` defaults to 1 and accepts 1–8 concurrent ordinary requests. Each response is checkpointed separately; an API error stops scheduling new requests while already-running requests finish and save their results. The job cost check covers the entire selected sample, regardless of worker count.

Latest model/prompt experiment: [alias wording retest](docs/alias-prompt-retest.md). The current extraction prompt is `extract-v4-no-conditional-aliases`; historical v2/v3 results remain readable.

The user-selected extraction default is now **Luna with medium reasoning**. [Full-corpus Batch preparation](docs/full-corpus-batch.md) records the four prepared local jobs and cost estimates. They have not been uploaded or submitted; starting is explicitly deferred.
