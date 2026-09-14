# Model quality comparison — 2026-09-14

**Newer results:** [Alias wording retest with both mini models and Luna](alias-prompt-retest.md).

## Decision

GPT-5 mini is a promising extraction candidate, but this experiment does **not** establish it as the best tested model or approve it for unattended full-corpus processing. The mini models handle more of the sample than the nano models. GPT-4.1 mini has a small structural advantage and better paired reviewer grounding scores; GPT-5 mini has somewhat better paired context scores. Repeated invented scoring rules and changed source conditions block production readiness.

The user prefers GPT-5 mini if its quality is sufficient. Keep that preference, but fix the extraction contract and test again before selecting a production model. No new Batch jobs were submitted in this evaluation.

## Method

- Same deterministic 36-unit development sample, seed 42: 18 tossups and 18 complete L/A/B/C bonus sets, with two units per tournament/question-kind stratum. Both school levels are represented. This is not a category-balanced or unseen holdout sample.
- Extraction prompt stayed `extract-v2-passages` for every candidate. GPT-5 used low reasoning and an 8,000-token output cap; historical GPT-4.1 jobs used 4,000-token caps without reasoning. This compares those configurations, not every possible setting for each model.
- Reused the first six saved GPT-5 responses, including the invalid mini response. Sent 30 new synchronous extraction requests per GPT-5 model. No GPT-5 extraction retries. Historical GPT-4.1 nano had one additional attempt on a failed smoke unit; retain that limitation.
- Reviewed every structurally valid candidate: 116 new synchronous GPT-5.4 reviews, low reasoning, 6,000-token cap. The reviewer received the original source and candidate but no extractor model identity. All 116 reviews validated.
- Used the same new `review-v4-source-contract` rubric across all four models. It explicitly checks prompt-only responses, exact acceptance conditions, invented scoring instructions, and passage support. Older review versions are preserved but excluded from this comparison.
- Checked 12 GPT-5 mini examples against their original context, compared several difficult examples across models, checked its 59 exported canonical answer identities against source answer lines, and inspected both reviewer passes from GPT-4.1 nano. These are Codex source audits, **not independent human gold labels**.

This follows the task-specific evaluation and grader-calibration approach described in [OpenAI’s evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

## Results

| Extractor | Structurally valid / 36 | Tossups / 18 | Bonuses / 18 | Review pass / reviewed | Units with a reviewer major issue |
| --- | ---: | ---: | ---: | ---: | ---: |
| GPT-5 mini | 31 | 17 | 14 | 0 / 31 | 30 / 31 |
| GPT-4.1 mini | 32 | 18 | 14 | 0 / 32 | 29 / 32 |
| GPT-5 nano | 26 | 18 | 8 | 0 / 26 | 26 / 26 |
| GPT-4.1 nano | 27 | 18 | 9 | 2 / 27 | 20 / 27 |

A structural failure means an unusable extraction under the current contract, even if its text contains useful information. Invalid units are included in the denominator of 36 but do not receive quality grades. A reviewer pass can include minor issues; it is not a guarantee of correctness. GPT-5 nano received two reject judgments; every other non-passing judgment was revise.

GPT-5 mini’s five structural failures were three uses of its own answer as clue evidence and two uses of a later bonus part. GPT-5 nano’s ten failures were four later-part references, three own-answer references, and three target-coverage failures.

### Paired comparison between the mini models

Both mini models produced reviewable outputs on the same 29 units. Comparing that intersection avoids giving one model an easier reviewed subset. Scores are advisory ordinal ratings from 1 to 5, not accuracy percentages or statistical proof.

| Dimension | GPT-5 mini | GPT-4.1 mini | GPT-5 mini wins / ties / losses |
| --- | ---: | ---: | ---: |
| answer accuracy | 3.45 | 3.76 | 5 / 14 / 10 |
| clue coverage | 4.34 | 4.45 | 4 / 17 / 8 |
| context handling | 3.76 | 3.59 | 12 / 9 / 8 |
| grounding | 2.62 | 3.10 | 4 / 10 / 15 |

The available evidence does not justify choosing GPT-5 mini on the claim that it performs best. It also does not establish GPT-4.1 mini as production-ready. These are single stochastic outputs from a small development sample, with no repeated-seed confidence estimate.

## Confirmed source-audit findings

| Source unit | Expected from source | Observed behavior |
| --- | --- | --- |
| 2020 TAILS / 7 / 10 (tossup) | The sun; also explicitly accept solar wind or solar flares. | Both mini models instead say not to accept those alternatives, overriding the source. GPT-5 nano omits the rule. |
| 2020 ERIS / 10 / 7 (tossup) | Prompt on cosmetics/beauty products; accept foundation only until foundation is mentioned. | GPT-5 mini puts prompt-only terms in accepted aliases. GPT-4.1 mini changes the cutoff to when “makeup” is mentioned. |
| 2021 CALISTO 2 / 7 / 1 / B | Prompt on “Ike”; accept Dwight David Eisenhower. | GPT-5 mini lists “Ike” as an accepted alias and also says to prompt on it. |
| 2022 SHOW-ME / 9 / 11 / B | Prompt on bare “integral”; accept time integral/equivalents. | GPT-5 mini accepts bare “integral” while also saying to prompt if necessary. |
| 2022 SHOW-ME / 5 / 11 (tossup) | Answer line only says Chicago. | GPT-5 mini adds accepted aliases and county/suburb rejection rules. GPT-5 nano adds pronunciation guidance and a sports category. |
| 2020 ERIS / 6 / 18 (bonus) | Separate A: Supreme Court; B: Louisiana; C: Maine and New Hampshire. | GPT-5 nano puts all three answers into A’s canonical answer. Structural validation did not detect this semantic conflation. |
| 2020 TAILS / 3 / 6 (tossup) | “fruits” is accepted only until “multiples of 3.” | GPT-5 mini preserves the cutoff in notes but also puts a conditional fruit entry in the general alias list. |
| 2022 KICKOFF Novice / 8 / 18 (bonus) | Facts about the ideal gas law and related quantities. | GPT-5 mini pads clues with “asked to name a law,” repeats a category, and invents scoring rules. |

The 59 exported canonical answer identities from GPT-5 mini matched the intended source answers in the source-line audit. This is a useful strength, but it excludes the five rejected units and does not validate aliases, adjudication, categories, or every clue. Core identification is substantially better than the current scoring-rule extraction.

### Reviewer limitations observed

The v4 reviewer incorrectly calls `[accept conservation of momentum]` a conditional accept in one mini review. The source provides no condition; that particular criticism should be discounted. It also inconsistently assigns major versus minor severity to invented rules and sometimes over-penalizes overlapping category tags. Raw grades remain unchanged for reproducibility. The source-confirmed errors above support the readiness decision independently of these grading flaws.

Both GPT-4.1 nano passes were inspected: the Jesus-miracles bonus (2020 TAILS / 4 / 5) has minor category issues but broadly faithful answers and clues; the E. coli tossup (2022 IQBT Regular Season Set 1 / 1 / 10) is broadly faithful. Two good outputs do not compensate for nine structural failures or establish nano as the overall winner.

## Required next changes

1. Separate **topic aliases** from **tournament-accepted responses**. A tournament can accept a related entity without declaring it the same topic; the current instruction to avoid related-entity aliases can conflict with preserving explicit source acceptance rules. Preserve the original answer line as authoritative.
2. Replace free-form invented adjudication with typed, source-backed accept/prompt/reject rules and explicit conditions. Require evidence from the answer line and leave absent rules absent. Do not let the model override tournament instructions using outside knowledge.
3. Restrict evidence choices per target in the output schema so a bonus part cannot cite later parts or its own answer. Retain semantic source review: valid references alone cannot prove support.
4. Re-run the development sample after these changes, then compare GPT-5 mini and GPT-4.1 mini on a new held-out sample with the same revised contract. Use independent human adjudication for difficult answer rules and grader disagreements before production. Keep all tests synchronous.

These changes are proposed next work; the extraction prompt/schema were deliberately unchanged during this comparison. No corpus-wide model processing was started.

## Cost and reproducibility

GPT-5 mini’s 36 extraction responses cost approximately **$0.090147**, including rejected responses; GPT-5 nano’s cost approximately **$0.027838**. The 116 new reviews cost approximately **$1.767969**. Excluding the previously paid six responses per GPT-5 model, this turn’s new generation cost was approximately **$1.87**. These are usage-based estimates at stored standard prices without cached-token discounts, not invoices.

The 36-unit mini sample projects to about $11.27 for 4,500 extraction units at standard rates, or $5.63 with Batch, excluding review/retries. Cost remains small; quality is the blocker.

All generated artifacts are under ignored `data/`; preserve them to retain paid work. Machine-readable matched statistics: `data/comparisons/quality-2026-09-14.json`. Each listed job includes source-linked `results.md`, `results.jsonl`, `report.json`, the immutable plan, and saved raw responses.

| Model | Extraction job | Review v4 job |
| --- | --- | --- |
| GPT-5 mini | `0c87b045561955817b7e0ebc` | `cff0dfdd9032d7648c75b87b` |
| GPT-4.1 mini | `70a39539442be80f747627f1` | `04e85c4956054bfc5badcc6d` |
| GPT-5 nano | `c07a23eb846f2106073985c0` | `d1babd91b64f414bd30f008f` |
| GPT-4.1 nano | `247817eaecd52339a7024226` | `8308c41a4b4147c05d8b1674` |

Reproduce the general comparison without API calls:

```bash
qb compare 0c87b045561955817b7e0ebc 70a39539442be80f747627f1 c07a23eb846f2106073985c0 247817eaecd52339a7024226
```

Use only the `review-v4-source-contract` breakdown for the new comparison. The CLI retains older reviewer versions separately.

Implementation changes in this evaluation: bounded `--workers` support for synchronous runs and the versioned review rubric. All **24 offline tests**, lint, and formatting checks passed. The concurrency test verifies that an in-flight success is checkpointed when another request fails.
