# Project guide

## Purpose and current status

Build a quiz-bowl study platform for middle- and high-school students. Teach broad, high-value recognition knowledge before obscure detail: topics, associations, clues, and relationships grounded in the question corpus. Questions are evidence for a curriculum as well as practice material.

Read `QUIZ_BOWL_PROJECT_HANDOFF.md` for the concise product vision and `docs/corpus-inspection.md` for verified findings and the proposed first implementation phase. Current user requirements and observed data supersede assumptions in the handoff. The repository contains corrected source data and a standalone Python processing CLI (`qb`) with deterministic ingestion, Responses API extraction, Batch job management, cached validation, and larger-model review. There is no student-facing application or resolved cross-corpus knowledge database yet. See `README.md` for setup and workflows.

## Repository and commands

- `*-school-tossups.csv`, `*-school-bonuses.csv`: source-controlled inputs; read-only during processing. Explicit user-authorized source corrections are recorded in the inspection notes and Git history.
- `QUIZ_BOWL_PROJECT_HANDOFF.md`: concise product vision and intended learning experience; operational guidance belongs here in `AGENTS.md`.
- `docs/corpus-inspection.md`: findings, known anomalies, and phased implementation plan.
- `scripts/inspect_corpus.py`: standard-library Python structural audit.
- `datasets.json`: explicit source-file, school-level, and question-kind manifest.
- `src/scholars_bowl/`: Python CLI, ingestion, extraction/review schemas, pricing, and Batch lifecycle.
- `tests/`: offline corpus and mocked API lifecycle tests.
- `pyproject.toml`: package/dependencies; installs the `qb` entrypoint.
- `README.md`: standalone CLI usage and model-evaluation workflow.
- `docs/pipeline-pilot.md`: initial live experiment, quality findings, exact job IDs, and continuation commands.
- `docs/model-quality-comparison.md`: matched 36-unit model evaluation, source audits, limitations, and next quality fixes.
- `AGENTS.md`: durable operating guide; update when architecture, commands, data conventions, or status change.

Run `python3 scripts/inspect_corpus.py` for the original structural audit. Install with `python3 -m venv .venv` and `.venv/bin/python -m pip install -e '.[dev]'`. Use `.venv/bin/qb ingest`, `prepare`, `run`, `smoke`, `submit`, `status`, `collect`, `review`, `report`, `compare`, and `retry` as documented in README. Run `.venv/bin/pytest -q`, `.venv/bin/ruff check src tests`, and `.venv/bin/ruff format --check src tests`. Generated snapshots, job plans/results, and caches live under ignored `data/`; back them up to preserve paid work. `.env` and `.venv/` are ignored. Keep reusable code, schemas, manifests, and tests source-controlled.

## School levels and provenance

The filename specifies `middle-school` or `high-school`; preserve this as explicit dataset metadata throughout ingestion and extraction. A canonical topic may appear in either or both levels. Model level membership through source-backed topic occurrences, not a single exclusive topic-level field. Retain tournament/set membership as well as school level, including after topic merges and splits.

Default middle-school practice to middle-school material. Default high-school practice to both levels. Let students choose levels. Apply the selection to question, clue/fact evidence, study content, and importance aggregation so a shared topic does not silently introduce high-school-only material into middle-school practice. Distinguish answer-target occurrences from contextual mentions. School level is not an inferred clue difficulty tier.

## Question model and mandatory data conventions

- Tossup columns: `Source, Round, Number, Question, Answer`.
- Bonus columns: `Source, Round, Number, Label, Question, Answer`.
- `Source` is tournament name/year; preserve round and number as source identifiers.
- Tossups are long, ordered questions designed for early buzzing. Preserve original text, order, and markers.
- A bonus is one contextual unit: lead-in `L` followed by answerable parts `A`, `B`, `C`. The lead-in is not a question. Store a parent set and ordered parts; extraction and practice must retain the lead-in and preceding-part context. Never process shuffled or isolated bonus rows as independent semantic inputs.
- Group bonuses by dataset/school level, source, round, and number, then order by label. Both files now use LABC order after a user-authorized correction; historical high-school input used ABCL. Never rely on physical adjacency or input order.
- Recognize exact schema header records wherever they occur. The high-school bonus header is the final record; the other headers are first. Blind `DictReader` header inference loses data here.
- All L rows now have empty Answer fields. Historical middle-school input repeated the lead-in there; those values were cleared at the user’s request. Lead-ins have no answer target.
- Matching tossup/bonus keys express the expected pairing, not a shared topic. Do not force thematic relationships. Flag missing or ambiguous pairs instead of silently inventing links.
- Use stable raw occurrence IDs based on source-file identity/version and CSV record ordinal (not physical line number). Natural source/round/number keys are not guaranteed unique. Preserve file hashes and original values; record normalized values and corrections separately.

Current baseline: 2,192 tossup records, 2,191 complete bonus sets, 6,573 bonus parts. The only remaining structural anomaly is the missing high-school bonus for `2020 TAILS / 10 / 20`; the user will check original documents. Keep it flagged without inventing a replacement. The erroneous Satanic Verses tossup at `2021 CALISTO 2 / 9 / 12` was removed after verifying it duplicated the bonus lead-in; bass remains the tossup. Bonus `2020 TAILS / 11 / 12 / C` now answers `Karl Marx`, supplied by the user. See the inspection notes for the correction history.

## Architecture direction

Keep three layers: immutable question bank → structured knowledge base → training engine. The current pipeline uses versioned JSON/JSONL artifacts and atomic checkpoints. A relational store is likely sufficient for the eventual knowledge base; PostgreSQL is a candidate, not an installed dependency or settled choice.

Model datasets, raw occurrences, tossups, bonus sets/parts, topics, aliases, facts/relationships, clue spans, evidence links, and eventually student progress. Topics may have multiple classifications and type-specific fields. Summaries should derive from supported structured knowledge. Every extracted assertion needs source occurrence/part IDs and ideally supporting text spans; bonus evidence may span multiple parts and the lead-in. Derived artifacts must retain extraction/version metadata and allow correction and regeneration.

Canonicalization must preserve raw answer lines alongside canonical names, aliases, adjudication rules, and unresolved candidates. Accept/prompt/reject rules, pronunciation notes, and conditional alternatives require careful parsing. Do not strip brackets/parentheses indiscriminately, merge solely by fuzzy similarity, or force descriptive/formula/multipart answers into a single entity. Support reviewed merges and splits with stable IDs.

There is no reliable category or difficulty column. Sparse answer-line tags and text markers are hints only. Preserve `(*)` and source annotations. Infer semantic clue boundaries separately from source order. Keep recognition tiers distinct from school level; derive importance from corpus recurrence, source breadth, position, and discriminative value only after validation. Avoid counting repeated imports or bonus lead-ins as additional answered questions.

## Processing and engineering rules

1. Inspect and ingest the full corpus deterministically before expensive semantic work. Use an explicit dataset manifest, strict CSV parsing, structural validation, and anomaly reports.
2. Assemble contextual units, normalize into separate fields, and identify repeated content without deleting occurrences. The user explicitly wants duplicates retained: recurrence across tournaments is useful evidence. Distinguish genuine source recurrence from accidental repeated imports.
3. Resolve topics and extract clues/facts using small, schema-validated semantic batches only where deterministic methods are insufficient. One bonus set stays together.
4. Cache and checkpoint by input identity plus parser/prompt/model/schema versions. Make reruns idempotent and failures resumable; retain intermediate artifacts and review decisions.
5. Aggregate level-aware topic evidence and importance, review outputs, then generate summaries and training material. Build training UI after trustworthy ingestion and knowledge extraction.

Never dump entire CSVs into agent context. Do not mutate source files during processing; explicit user-authorized corrections are permitted and must be documented and verified against the prior version. Use CSV-aware scripts with encoding, quoting, embedded-newline, field-size, and malformed-record handling. Bring aggregate statistics and small reproducible samples into context. Never silently skip malformed rows.

Use Python 3.11+, argparse, the OpenAI Python SDK, Pydantic, python-dotenv, filelock, and tiktoken. Tests use pytest and never require a key or paid calls. Preserve coverage of CSV edge cases, full-corpus counts, stable IDs, school-level provenance, context/evidence validation, unordered/partial Batch outputs, idempotent submission, recovery, and cache reuse. Model-backed testing uses explicit synchronous run/smoke commands, never ordinary unit tests. Batch is reserved for large-scale processing.

## Next work and open decisions

Evaluate the pilot outputs before scaling semantic processing. The first extraction pass produces answer-target candidates, aliases/adjudication notes, categories, and recognition facts with evidence. `extract-v4-no-conditional-aliases` retains the deterministic numbered text passages introduced in v2 and supplies them so models select evidence instead of copying quotes; Python supplies the exact spans. These mechanical spans are not semantic clue boundaries. Legacy v1 quote-based artifacts remain readable. Blinded larger-model review is advisory, never ground truth or an automatic promotion to curriculum. Defer polished UI, elaborate ontology, graph infrastructure, and corpus-wide model calls. Next phases include cross-corpus entity resolution, reviewed merges/splits, human corrections, explicit fact relationships, level-aware topic aggregation, and study generation. Refine taxonomy, adjudication representation, quality thresholds, duplicate-aware scoring, and importance weighting based on evidence. Verify source usage rights before publishing question text. Keep this guide factual: distinguish implemented behavior from proposals, and record new commands and verified findings as work progresses.

## API execution conventions

The user authorized reuse of the project `.env` key for pipeline work. Do not print secrets or raw API exception messages (authentication errors may echo a key). Read the key only for API commands; offline ingestion, preparation, reporting, and tests need no key. Nano/mini extraction profiles are pinned GPT-5 nano/mini snapshots with low reasoning; GPT-4.1 profiles remain explicit historical baselines; the reviewer is pinned GPT-5.4 with low reasoning after GPT-4.1 review missed known errors; models and explicit prices are configurable. Prices are dated, and cost thresholds are padded estimates rather than guaranteed dollar caps. User model selection: use GPT-5.6 Luna with medium reasoning for full-corpus extraction. Preparation is authorized; submission is explicitly not yet authorized. At the observed sample cost, extraction expense is negligible to the user; prioritize quality over further nano cost optimization. Sample-based projections are estimates, not spending ceilings, and exclude separate review and retry costs. User preference: all testing and pilot reviews use synchronous API requests (`qb run` or `qb smoke`). Reserve Batch for large-scale production processing, not test samples. Do not submit new pilot batches.

Job plans include source, prompt/schema, model, and request settings in their identity. Do not edit submitted plans. Collect terminal outputs before retrying failures or submitting overlapping jobs. Preserve valid caches and raw failures. After an uncertain Batch creation, use `recover`; never blindly repeat creation. Bump prompt/parser versions when their semantics change and retain compatibility or an explicit migration error for existing artifacts. School levels are attached deterministically, not inferred by the model.

## Quality evaluation update — 2026-09-14

The matched 36-unit GPT-5 follow-up is documented in `docs/model-quality-comparison.md`. GPT-5 mini validated 31/36 and GPT-5 nano 26/36, compared with historical GPT-4.1 mini 32/36 and nano 27/36. These are structural checks, not accuracy. Source audits found invented scoring rules, prompt-only aliases, and reversal of explicit source accepts. No model is approved for unreviewed full-corpus extraction, and GPT-5 mini has not been established as best. The reviewer prompt is now `review-v4-source-contract`; compare all models using this same version, and retain older judgments separately. Reviewers can also misread unconditional accepts as conditional; check source evidence before treating grades as truth. Next, separate source-backed scoring rules from topic aliases, constrain evidence per target, and evaluate on an unseen sample after revising the extraction contract. `qb run` and `qb smoke` support `--workers 1–8` (default 1) for bounded concurrent ordinary API requests, with per-response checkpoints and no automatic retries.

## Alias prompt retest — 2026-09-14

See `docs/alias-prompt-retest.md` for the latest experiment. Only the alias wording changed in `extract-v3-explicit-aliases`; all other extraction instructions and schemas stayed fixed. On the same 36 units, GPT-5 mini validated 35 and passed 1/35 reviews; GPT-4.1 mini validated 33 and passed 3/33; GPT-5.6 Luna (medium reasoning) validated 36 and passed 15/36. Luna was strongest in this retest and is recommended for the next experiment, not yet approved for unattended processing. The CLI now offers `--profile luna` using `gpt-5.6-luna`, medium reasoning, and standard rates $0.20/M input and $1.20/M output verified in official model docs. Existing mini default remains unchanged. Preserve historical v2 results. Next, clarify that conditional accepts stay out of aliases, preserve exact conditions, and forbid invented adjudication notes; then use an unseen validation sample. The current reviewer is stricter about conditional aliases than the extraction prompt explicitly states, and can falsely call unconditional accepts conditional. Keep grading advisory.

## Full-corpus preparation — current decision

The user selected Luna with medium reasoning and requested one additional sentence excluding conditionally accepted answers from aliases. Current extraction prompt is `extract-v4-no-conditional-aliases`; v2/v3 artifacts remain readable. The CLI extraction default is now `luna` (medium, 8,000 output tokens). Earlier model-selection cautions above are historical findings, not requirements to repeat the pilot before the user-selected preparation. Four disjoint full-corpus jobs are prepared locally, covering all 4,383 units. See `docs/full-corpus-batch.md` and `data/production/luna-v4-preparation.json` for exact IDs, hashes, costs, and future commands. Estimated Batch extraction cost is $2.19 from pilot usage, or $21.74 at the padded output-cap estimate. **Do not submit, upload, or start processing until the user authorizes starting.** Nothing in this preparation was uploaded or run through a model. Preserve the missing bonus anomaly and repeated occurrences.
