# Pipeline pilot — 2026-09-14

**Newer results:** [Alias wording retest with both mini models and Luna](alias-prompt-retest.md).

**Latest quality results:** See [the matched 36-unit comparison](model-quality-comparison.md). GPT-5 mini is not yet established as best or ready for unattended processing.

**Workflow update:** This records the historical GPT-4.1 pilot. At the user’s direction, current extraction defaults are GPT-5 nano/mini and all new testing/review runs are synchronous. Batch is reserved for large-scale processing. Previously submitted jobs are retained; do not recreate this Batch testing workflow.

The standalone `qb` CLI is implemented and has processed the complete source corpus through deterministic ingestion. Source CSVs were unchanged during this implementation. Live extraction used a fixed 36-unit sample: two units per tournament/question-kind combination, including both school levels. Every bonus request included its full L/A/B/C context.

## Findings

The initial quote-copying prompt (`extract-v1`) failed validation on 1/2 nano responses and 5/6 mini responses. Models dropped source markers and paraphrased quotes. This led to `extract-v2-passages`: Python assigns passage IDs and supplies verbatim text and offsets after the model selects evidence. This improved structural reliability without relaxing provenance checks.

| Candidate | Valid units / 36 | Valid tossups / 18 | Valid bonus sets / 18 |
| --- | ---: | ---: | ---: |
| GPT-4.1 nano | 27 | 18 | 9 |
| GPT-4.1 mini | 32 | 18 | 14 |

These are **schema/context validation results, not factual accuracy scores**. Each candidate received six synchronous smoke attempts; the remaining unvalidated requests were submitted through Batch. One failed nano smoke unit was therefore attempted again in Batch. The final numbers include that retry opportunity. Mini's four rejected units used later bonus parts or the target's own answer as clue evidence. Nano's nine rejected units included later-part leakage, missing/duplicated target coverage, and one incomplete response. Successful candidates are cached; failures and raw output remain inspectable.

The initial larger reviewer, GPT-4.1, approved all 11 available validated smoke extractions. Agent spot-checking found errors it missed:

- Prompt-only terms such as “cosmetics” and “beauty products” were treated as aliases for “makeup.”
- A conditional acceptance rule for “foundation” was changed from “until mentioned” to a condition involving the word “makeup.”
- Unsupported adjudication notes were added, including rejection rules not present in the answer line.
- An author of science fiction was tagged as science, and a city was tagged as media.

GPT-5.4 with low reasoning was more discriminating on the same candidates: its valid smoke reviews requested revisions on all four reviewed nano outputs and four of six mini outputs; two mini outputs passed. One of five nano reviews referenced a nonexistent target and was rejected. Review schema v3 now restricts issue labels to the actual target labels. GPT-5.4 is the default reviewer; the old reviewer remains available as `reviewer-baseline` for comparison. Neither reviewer is ground truth, and there is no automatic curriculum approval.

Within the historical GPT-4.1 comparison, the evidence favors mini over nano for this task, particularly for bonuses. It does **not** establish that mini is ready for unreviewed full-corpus processing.

## Exact jobs and outputs

All paths below are relative to `data/jobs/`. Generated data is ignored by Git; preserve it to retain paid work.

| Purpose | Job ID | State at this handoff |
| --- | --- | --- |
| Nano 36-unit extraction | `247817eaecd52339a7024226` | Collected; 27 validated |
| Mini 36-unit extraction | `70a39539442be80f747627f1` | Collected; 32 validated |
| GPT-5.4 nano smoke review, v2 | `7be90df5bba8ceccb6d9c89f` | 4 valid reviews; 1 rejected |
| GPT-5.4 mini smoke review, v2 | `56f8ca96ff768a7b54a772d4` | 6 valid reviews |
| GPT-5.4 nano full pilot review, v3 | `0081bc6b6c5a1de60098eff8` | Batch submitted; collect later |
| GPT-5.4 mini full pilot review, v3 | `38d8a1f1dfb21cc412e3c358` | Batch submitted; collect later |

Each reported job contains `results.md`, `results.jsonl`, and `report.json`. Batch extraction failures are summarized in `collection.json`; original responses remain in `batch-output.jsonl`. The comparison is `data/comparisons/a452a61172977359c17b3bf9.json`, with separate breakdowns by reviewer model and prompt version.

Completed live smoke and extraction Batch responses cost approximately **$0.195** at the recorded prices, including invalid responses. This is a usage-based estimate without cached-token discounts, not an invoice. The two queued full pilot reviews have a combined padded estimate of **$2.77 at their output-token caps**; actual usage is likely lower. These estimates do not impose a provider-side dollar ceiling.

## Continue from the terminal

```bash
source .venv/bin/activate
qb status 0081bc6b6c5a1de60098eff8
qb status 38d8a1f1dfb21cc412e3c358
qb collect 0081bc6b6c5a1de60098eff8
qb collect 38d8a1f1dfb21cc412e3c358
qb report 0081bc6b6c5a1de60098eff8
qb report 38d8a1f1dfb21cc412e3c358
qb compare 247817eaecd52339a7024226 70a39539442be80f747627f1
```

`collect` returns safely if a batch is still running. No local process needs to stay open. Nothing automatically submits the entire corpus.

Next, inspect review disagreements and create a small human-reviewed reference set. Tighten answer-rule extraction and category definitions, constrain bonus evidence more strongly, then evaluate a held-out sample. Consider a newer small model or routing more difficult bonuses to a stronger model. Only then expand to larger slices of the corpus. Cross-corpus topic resolution and study-summary generation remain subsequent phases.

## GPT-5 synchronous follow-up

Current `nano` and `mini` profiles use `gpt-5-nano-2025-08-07` and `gpt-5-mini-2025-08-07`, respectively, with low reasoning effort. GPT-4.1 remains available through explicit baseline profiles. `qb run` performs synchronous testing (default limit 36); all new pilot extraction and review work uses this path. Batch remains available for large-scale processing only.

The same first six sample units were tested with the unchanged passage-reference prompt, an 8,000-token output cap including reasoning, and no retries:

| Model | Job ID | Valid / attempted | Estimated cost of all six responses |
| --- | --- | --- | --- |
| GPT-5 nano | `b40c1c446bf38d5d542b673b` | 6 / 6 | $0.003972 |
| GPT-5 mini | `552a84a0a912349a8aaaa864` | 5 / 6 | $0.013769 |

Mini's rejected response used its target's own answer as recognition-clue evidence. These are structural/evidence-reference validation results, not factual accuracy measurements; the six-unit sample does not establish a model winner. Costs use returned usage at standard listed rates without cache discounts, including the invalid mini response. Larger-model and human quality review of these new candidates remains pending.

The previously submitted GPT-5.4 review of the 32 validated GPT-4.1 mini results (`38d8a1f1dfb21cc412e3c358`) has now been collected: all 32 reviews validated; 28 requested revisions and four passed. These reviews are advisory. No new pilot Batch jobs were submitted for the GPT-5 follow-up.
