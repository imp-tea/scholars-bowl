# Corpus inspection and correction history

Inspected 2026-09-14 using Python's CSV reader, strict UTF-8 decoding, aggregate statistics, and beginning/middle/end plus seed-42 samples. All records parse with comma delimiters and standard CSV quoting; all records have the expected width. The initial inspection did not modify inputs. The current counts below reflect subsequent user-authorized corrections on the same date; original data remains in Git history.

| File | Bytes | Data rows | Logical groups | Header record |
| --- | ---: | ---: | ---: | ---: |
| high-school-tossups.csv | 969,465 | 1,532 | 1,532 tossup keys | 1 |
| high-school-bonuses.csv | 1,357,662 | 6,124 | 1,531 bonus sets | 6,125 |
| middle-school-tossups.csv | 324,897 | 660 | 660 tossup keys | 1 |
| middle-school-bonuses.csv | 531,936 | 2,640 | 660 bonus sets | 1 |

There are 2,192 tossup records and 2,191 bonus sets containing 6,573 answerable parts: 8,765 answerable records in total, plus 2,191 lead-ins. The handoff's estimate of roughly 6,000 high-school questions is superseded by these counts and the inclusion of middle school.

## Schemas and sources

- Tossups: `Source, Round, Number, Question, Answer`.
- Bonuses: `Source, Round, Number, Label, Question, Answer`.
- School level comes from the filename, not a CSV column. Source names identify tournament/year; round and number are source identifiers.
- High school: 2020 TAILS, 2021 CALISTO 2, 2022 IQBT Regular Season Set 1, 2022 KICKOFF Novice, 2022 SCOP Novice 12, 2022 SHOW-ME.
- Middle school: 2020 ERIS, 2022 SANDS, 2022 SCOP MS 11.

## Structural findings and anomalies

- Every bonus group has exactly one each of L/A/B/C. Both files now use LABC order; high-school groups were originally ABCL. Group by school level/source/round/number and reconstruct LABC explicitly.
- All 2,191 lead-in answers are now empty. The 660 middle-school lead-ins originally repeated the question text in Answer; those repetitions were cleared. Lead-ins are not answerable questions.
- High-school tossup `2021 CALISTO 2 / 9 / 12` now contains only bass. The erroneous Satanic Verses row was verified to exactly duplicate that bonus set’s lead-in text and was removed as directed. There are no remaining duplicate tossup keys.
- High-school tossup `2020 TAILS / 10 / 20` has no bonus group. Every other tossup key has a bonus key; no bonus key lacks a tossup key. This remains unresolved while the user checks the original documents; do not invent a replacement.
- Bonus `2020 TAILS / 11 / 12 / C` now has the user-supplied answer `Karl Marx`. No answerable records have empty answers.
- No exact duplicate full rows occur. High-school bonuses have nine repeated text/answer pairs; retain these and any other repeated question occurrences per the user’s direction. Recurrence across tournaments is useful evidence; future scoring should distinguish this from accidental repeated imports. Near-duplicate semantic analysis remains pending.
- No question text or source/round/number/label fields are empty.

## User-authorized corrections (2026-09-14)

- Reordered all 1,531 high-school bonus groups from ABCL to LABC while retaining group order and the existing final header record.
- Cleared Answer on all 660 middle-school lead-in records, preserving their Question text.
- Removed exactly one erroneous high-school tossup, The Satanic Verses at `2021 CALISTO 2 / 9 / 12`, after matching its full Question text to the bonus L record. The original high-school tossup count was 1,533; it is now 1,532.
- Replaced the empty Answer at `2020 TAILS / 11 / 12 / C` with `Karl Marx` at the user’s direction. This is a user-supplied correction, not a claim of independent source verification.
- Left the missing bonus unresolved and retained all repeated content occurrences.

Verified all CSV record multisets against the pre-correction Git version with only these authorized changes applied. Confirmed both bonus files have only LABC groups, all lead-in answers are empty, no answerable answers are empty, and no duplicate tossup keys remain. Middle-school tossups are byte-for-byte unchanged. The audit still reports exactly the known missing bonus key.

## Text and semantic implications

There are no category, subcategory, difficulty, or clue-span columns. Some middle-school answer lines contain category/author tags such as `<American History–Kapadia>` or `<Sethi, Science>` (60 tossup and 81 bonus rows contain angle brackets). These are incomplete, inconsistent hints, not a corpus-wide taxonomy. Category distributions cannot yet be stated reliably. Samples cover literature, history, science/math, fine arts, religion/mythology, geography, and popular culture; complete classification remains future work.

Answer lines include `ANSWER:`, square-bracket and parenthetical alternatives, accept/prompt/reject instructions, pronunciation guides, and conditional rules such as “until read” or “before mention.” Parentheses and brackets are not always disposable annotations. Examples include sine with an alternative “sine of x,” Soviet Union with many aliases and prompt rules, and a descriptive answer about ascending bodily to heaven. Entity-like answers coexist with formulas, descriptive phrases, and potentially multipart answers; a reliable proportion needs semantic review rather than a punctuation heuristic.

Tossup text preserves clue order, usually moving from specific clues toward a giveaway in inspected samples. `(*)` appears in 1,412 high-school and 640 middle-school tossups; preserve it as a source marker, not a complete segmentation or verified difficulty label. No explicit clue boundaries exist. Bonus text sometimes includes `[E]`, `[M]`, `[H]`, or `[10]`; retain these as source annotations pending source-specific interpretation. School level, source difficulty hints, and inferred recognition tiers must remain separate.

Historic/current-event statements must retain tournament context rather than become timeless facts. Canonicalization must allow ambiguous topics and non-entity answers. Bonus extraction must see the entire ordered set; a part's evidence can include its lead-in and earlier parts.

## First implementation phase

1. Build a full-corpus deterministic importer with an explicit file manifest (school level and question kind), file hashes, immutable raw records, header recognition anywhere, stable occurrence IDs, and validation reports.
2. Assemble bonus sets in LABC order and report missing/ambiguous tossup links. Keep anomalous records available for review without treating them as valid practice items.
3. Add separate normalized text/answer candidates and source annotations, exact/near-duplicate candidates, and a correction log. Validate counts against this audit.
4. Introduce versioned, resumable semantic extraction batches: full tossups or full bonus sets. Resolve topics conservatively, retain role-specific evidence and level membership, then extract supported clues/facts.
5. Review representative output before scaling semantic processing across all records; aggregate importance per selected school levels before generating summaries or training material.

No model calls or app implementation were performed. Run `python3 scripts/inspect_corpus.py` to reproduce the structural audit. Entity-answer proportions, semantic duplicates, taxonomy, scoring, and source usage rights remain unresolved.
