# Alias prompt retest — 2026-09-14

## Conclusion

The shorter alias instructions improved the observed results, but did not eliminate conditional-answer or invented-adjudication problems. **GPT-5.6 Luna with medium reasoning was the strongest candidate in this retest.** Keep the revised wording and use Luna for the next development/held-out evaluation. This is not approval for unattended full-corpus processing; the default mini profile has not been silently replaced.

## Exact prompt change

The previous wording was still present:

> Aliases must be explicitly acceptable equivalents in the answer line, not merely prompt-on answers, rejected answers, or related entities.

It was replaced with:

```text
Aliases must be acceptable equivalents explicitly stated in the answer line.
Do not include prompt-on answers in aliases.
Do not include rejected answers in aliases.
Do not invent aliases that are not explicitly mentioned in the source.
```

This is `extract-v3-explicit-aliases`. All other extraction instructions, schemas, source passage segmentation, and validation rules were unchanged. Earlier `extract-v2-passages` and v1 results remain readable.

## Controlled setup

- Same 36 development units: 18 tossups and 18 complete bonus sets, seed 42, both school levels. No new corpus-wide processing or Batch requests.
- GPT-5 mini: `gpt-5-mini-2025-08-07`, low reasoning, 8,000 output tokens. GPT-4.1 mini: `gpt-4.1-mini-2025-04-14`, no reasoning setting, 4,000 output tokens. Source units and complete request bodies were verified identical to the earlier run except for extraction instructions.
- New candidate: the exact requested `gpt-5.6-luna`, medium reasoning, 8,000 output tokens. Access was verified with the project key; all returned model IDs were saved. Luna had no old-prompt control run.
- One new response per unit/model, no retries. Eight concurrent ordinary Responses requests per run, checkpointed individually.
- All 104 structurally valid extractions received the same blinded GPT-5.4 low-reasoning review with `review-v4-source-contract` and a 6,000-token cap. All 104 reviews validated.

Luna’s API availability, medium reasoning support, and standard rates ($0.20/M input, $1.20/M output) were checked against its [official model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

## Results

| Configuration | Structurally valid / 36 | Quality-review passes / reviewed | Reviewer major-issue units | Extraction cost, all 36 attempts |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.6 Luna | 36 | 15 / 36 | 13 / 36 | $0.035920 |
| GPT-5 mini | 35 | 1 / 35 | 32 / 35 | $0.089119 |
| GPT-4.1 mini | 33 | 3 / 33 | 27 / 33 | $0.037104 |

Previously, GPT-5 mini validated 31/36 and passed 0/31 reviews; GPT-4.1 mini validated 32/36 and passed 0/32 reviews under the same reviewer version. Revised results are 35/36 and 1/35 for GPT-5 mini, and 33/36 and 3/33 for GPT-4.1 mini. This is a single stochastic rerun on an already-used sample, not proof of generalization or a precise causal effect size.

Luna also led on matched reviewed subsets, so its higher scores are not merely a result of reviewing different units:

| Paired subset | Answer/rule accuracy | Grounding | Clue coverage | Context |
| --- | --- | --- | --- | --- |
| Luna / GPT-5 mini, 35 units | 4.60 / 3.91 | 4.29 / 3.03 | 4.51 / 4.23 | 4.46 / 3.57 |
| Luna / GPT-4.1 mini, 33 units | 4.58 / 4.06 | 4.27 / 3.54 | 4.51 / 4.51 | 4.42 / 3.82 |

Scores are advisory 1–5 ratings, not measured accuracy percentages. Invalid extractions remain failures in the 36-unit denominator and do not receive quality reviews.

## Direct checks of the requested alias behavior

Five source answer lines explicitly mark six prompt-only terms: cosmetics/beauty products, integral, Ike, plants, and Russia. Checked these terms in the raw outputs, including outputs rejected for unrelated structural reasons.

| Model | Old prompt: cases incorrectly including prompt-only aliases / 5 | Revised prompt / 5 |
| --- | ---: | ---: |
| GPT-5 mini | 3 | 1 |
| GPT-4.1 mini | 2 | 1 |
| Luna, medium reasoning | Not tested | 0 |

GPT-5 mini still included bare “integral”; GPT-4.1 mini still included “Ike.” All three kept cosmetics/beauty products out of aliases in the revised makeup example. These are focused checks of explicit terms, not an exhaustive alias-accuracy metric. The complete alias lists, source answer lines, and notes are saved in `data/comparisons/alias-retest-source-checks.json`.

## Remaining issues and grader checks

- All three put conditionally accepted **fruits** in the general alias list, despite its “until multiples of 3” cutoff. Both mini models also put conditional **foundation** there; Luna kept foundation only in notes. The extraction prompt says to put conditions in notes, but does not yet explicitly say conditional answers must be excluded from aliases. The reviewer assumes that exclusion. This remaining instruction mismatch should be resolved before treating all such flags as model failures.
- Luna preserves the source’s solar-wind/solar-flares acceptance but calls it conditional, although the source states no condition. Its Chicago notes still invent a rejection/prompting rule. Shortening alias instructions alone did not constrain every adjudication field.
- Luna omits the Gallipoli/ANZAC lead-in clue for New Zealand. In the Lahiri bonus, one MIT-library clue cites only the trailing fragment of a mechanically split sentence, so its references do not support the complete statement.
- Audited four reproducibly selected Luna passes (random seed 613): Journey to the West bonus, Akira Kurosawa tossup, ideal-gas-law bonus, and makeup tossup. These are largely faithful, though the makeup extraction loses the useful Elizabeth I association despite a reviewer pass. Also inspected all four passes from the mini models: one Supreme Court clue omits the first Marbury passage from its citations.
- The reviewer again wrongly treats the source’s plain “accept conservation of momentum” as conditional, and is sometimes overly literal about equivalent phrasing. Its raw grades are retained without silent correction. These are Codex source audits, not independent human gold labels.

Recommended next prompt experiment: explicitly exclude conditional answers from aliases, preserve their exact source conditions in notes, and prohibit invented adjudication rules or pronunciation guidance. Distinguish an unconditional “accept X” from an explicit “accept X until/if …” rule. Evaluate Luna with those clarifications on this development sample and then an unseen sample before scaling.

## Reproduction and cost

Added `--profile luna`, which defaults to medium reasoning. Example:

```bash
qb prepare --profile luna --reasoning medium --limit 36 --seed 42
qb run JOB_ID --limit 36 --workers 8 --max-cost 0.40
qb review JOB_ID
qb run REVIEW_JOB_ID --limit 36 --workers 8 --max-cost 3.50
```

| Model | Extraction job | Review job |
| --- | --- | --- |
| GPT-5.6 Luna | `82f68b78039ec599664026ab` | `a42a13e30d7227a097d69225` |
| GPT-5 mini | `70b2627980d550aad0b44c72` | `f352ecd764c20e74214bd6bd` |
| GPT-4.1 mini | `a49cc0fdaf2de1982bcd5eb1` | `2c84f48afe04db2a33d28071` |

Generated statistics: `data/comparisons/alias-retest-summary.json`; immutable job manifest: `data/comparisons/alias-retest-manifest.json`. Each job contains source-linked `results.md`, `results.jsonl`, raw responses, and the request plan. These generated artifacts are ignored by Git; preserve them to retain paid work.

Total new generation cost was approximately **$1.52**, including 108 extractions, rejected extraction outputs, and 104 reviews. Estimates use returned usage at stored standard rates without cached-token discounts, not billing invoices.

All **25 offline tests**, lint, and formatting checks passed. The added compatibility test verifies that v2 passage outputs still validate and retain identical evidence spans after the prompt revision.
