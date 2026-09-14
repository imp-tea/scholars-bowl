# Quiz Bowl Training Platform — Project Handoff for Codex

## Purpose of this document

You are taking over development of a new quiz-bowl training platform from an earlier design conversation. The project folder contains several large CSV files with roughly 6,000 high-school quiz-bowl questions in total.

Your first job is **not** to immediately start coding the whole application. First, inspect the repository and the question data carefully, learn the real structure and characteristics of the dataset, and then refine the product/data architecture described below based on what is actually present.

After that initial investigation, create an `AGENTS.md` file in the project root that serves as the durable project brief and operating guide for every future coding agent working in this repository.

Do not treat the ideas in this document as immutable requirements. They are the current design direction. Improve them when the data suggests a better approach.

---

# Product vision

The goal is to build an unusually effective training website for high-school quiz-bowl students.

Students are assigned broad specialties such as:

- English / Literature
- Math / Science
- History, including US and world history
- Sports / Media / Miscellaneous / popular culture

The training goal is **broad recognition knowledge**, not deep mastery of every subject.

For example, a literature specialist should not need to read every novel that might appear in competition. Instead, the system should teach enough high-value information that the student can recognize clues early:

- `Frankenstein`
- Mary Shelley
- Gothic novel
- published in 1818
- Victor Frankenstein creates a sentient creature
- Robert Walton
- subtitle `The Modern Prometheus`

A student who has absorbed those associations may be able to buzz correctly well before the giveaway clue.

The platform should therefore turn the existing question corpus into a structured **quiz-bowl curriculum** consisting of topics, facts, associations, clue patterns, and relationships.

Think of the source questions as evidence for what students ought to recognize, rather than merely as a bank of questions to replay.

---

# Core conceptual architecture

The current design separates the system into three layers:

1. **Question bank**
   - The original imported questions and answers.
   - Preserve source text and provenance.

2. **Knowledge base / wiki / knowledge graph**
   - Topics such as people, books, events, scientific concepts, works of art, sports figures, etc.
   - Structured facts and relationships between topics.
   - High-value recognition clues extracted from the source corpus.
   - Human-readable study summaries.

3. **Training engine**
   - Topic study pages.
   - Quick recall questions.
   - Progressive clue / buzz practice.
   - Spaced repetition.
   - Student mastery tracking at the clue/fact level when practical.

The website should feel partly like a concise wiki and partly like a purpose-built spaced-repetition trainer.

---

# Topic-oriented wiki

The central user-facing object should probably be a **Topic**.

Example conceptual topic:

```text
Topic: Frankenstein
Type: Literary Work

Canonical answer:
    Frankenstein; or, The Modern Prometheus

Aliases:
    Frankenstein
    The Modern Prometheus

Author:
    Mary Shelley -> topic link

Published:
    1818

Genres:
    Gothic fiction -> topic link
    Science fiction -> topic link

Characters:
    Victor Frankenstein
    The Creature
    Robert Walton
    Elizabeth Lavenza

Recognition clues:
    scientist creates a living creature
    Victor Frankenstein
    unnamed creature
    Robert Walton's letters
    University of Ingolstadt
    "Modern Prometheus"
    Mary Shelley

Summary:
    concise study-oriented summary...

Source questions:
    references to every source question supporting this topic/fact set
```

Topics should link to other topics wiki-style.

For example:

```text
Mary Shelley
    WROTE -> Frankenstein
    MARRIED_TO -> Percy Bysshe Shelley
    CHILD_OF -> Mary Wollstonecraft
    ASSOCIATED_WITH -> Lord Byron
    ASSOCIATED_WITH -> Romanticism

Frankenstein
    WRITTEN_BY -> Mary Shelley
    GENRE -> Gothic fiction
    CONTAINS_CHARACTER -> Victor Frankenstein
    PUBLISHED_IN -> 1818
```

A student reading about `Frankenstein` should be able to follow links to `Mary Shelley`, `Gothic fiction`, `Romanticism`, etc.

---

# Topics versus clues/facts

Avoid storing everything as undifferentiated AI-generated prose.

Prefer a structure where:

```text
Question
   -> evidence for clues/facts
   -> clues/facts connect topics
   -> summaries are generated from structured knowledge
```

For example:

```text
Mary Shelley --WROTE--> Frankenstein
Waterloo --OCCURRED_IN_YEAR--> 1815
Mitosis --PRODUCES--> two daughter cells
Quadratic formula --USES--> discriminant b^2 - 4ac
Michael Jordan --PLAYED_FOR--> Chicago Bulls
```

This structure will make it much easier to:

- generate quizzes,
- rank important facts,
- detect duplicates,
- correct bad extractions,
- update summaries,
- track student learning,
- and trace information back to source questions.

Preserve provenance wherever feasible.

---

# Topic templates

Different kinds of topics should expose different useful fields.

Possible initial topic types include:

| Topic type | Example useful fields |
|---|---|
| Literary work | author, publication date, genre, characters, plot, famous scenes, related works |
| Author | nationality, period, major works, style/movement, contemporaries |
| Historical event | date, place, causes, participants, outcome, significance |
| Person | dates, roles, accomplishments, associated events |
| President / leader | term, party or affiliation, major legislation, conflicts, accomplishments, related people/events |
| Country / place | capital, geography, history, major people/events, cultural associations |
| Scientific concept | definition, components, mechanism/process, related concepts |
| Scientist | field, discoveries, experiments, publications, awards |
| Biological structure | function, location, components, processes |
| Mathematical concept | definition, formulas, examples, related concepts |
| Artwork | artist, date, medium, movement, subject, location |
| Composer / musical work | composer, era, form, motifs, associated works |
| Sport / athlete / team | accomplishments, championships, records, associated teams/people |
| Film / TV / media | creator, performers, characters, plot, release, awards |

These templates are starting points. Inspect the actual corpus before deciding which types are warranted and how granular they should be.

A topic may need multiple classifications.

---

# Recognition clues are a first-class feature

The training system should explicitly teach associations that help a player recognize an answer from clues.

Examples:

```text
"Modern Prometheus" -> Frankenstein
Victor Frankenstein -> Frankenstein
Mary Shelley -> Frankenstein
Robert Walton -> Frankenstein
Ingolstadt -> Frankenstein

Gettysburg Address -> Abraham Lincoln
Emancipation Proclamation -> Abraham Lincoln
John Wilkes Booth -> Abraham Lincoln
```

Experienced players accumulate these associations implicitly. This platform should teach them deliberately.

Look for ways to model clue strength or usefulness rather than treating all facts as equally valuable.

---

# Corpus-derived importance

Prefer deriving importance from the actual question set rather than asking an LLM to invent a generic curriculum from world knowledge.

Repeated concepts and repeated clues in the source corpus are especially valuable signals.

Potential inputs into an importance score include:

- number of distinct source questions containing/supporting the clue,
- how early the clue appears in a question,
- whether the clue is highly discriminative for one answer,
- whether it is a common giveaway versus a difficult early clue,
- breadth across different question sets/files,
- category/subcategory frequency.

Do **not** hard-code this formula before inspecting the data. Determine what information the CSVs actually contain and what can reliably be measured.

---

# Difficulty / recognition tiers

A useful curriculum may organize clues for a topic into approximate layers such as:

### Level 1 — essential recognition

```text
Frankenstein
Mary Shelley
1818
Gothic novel
Victor Frankenstein
scientist creates a living creature
```

### Level 2 — competitive recognition

```text
Robert Walton
Elizabeth Lavenza
Ingolstadt
The Modern Prometheus
Lake Geneva
```

### Level 3 — deeper clues

```text
De Lacey family
Justine Moritz
William Frankenstein
Mont Blanc
Safie
```

The pedagogical priority is generally:

> broad Level-1 knowledge across many topics before deep Level-3 knowledge across a small number of topics.

Investigate whether the source questions provide enough structure to infer such tiers automatically, perhaps from clue position, recurrence, or question difficulty.

---

# Student-facing training modes

A topic page should eventually support a `Quiz me on this topic` action.

Possible modes include:

## Quick recall

After reading a short topic summary, ask a handful of focused retrieval questions.

Example:

```text
Who wrote Frankenstein?

What genre is Frankenstein strongly associated with?

Who creates the creature?

Approximately when was the novel first published?
```

## Buzz practice

Reveal clues progressively, imitating quiz-bowl gameplay:

```text
This novel contains a framing narrative told through letters written by Robert Walton...

[BUZZ]

Its protagonist studies at the University of Ingolstadt...

[BUZZ]

The protagonist creates a living creature...

[BUZZ]

This 1818 novel was written by Mary Shelley.

[BUZZ]
```

Reward earlier correct answers more strongly.

If practical, show what recognition clue the student missed or where the answer became obvious.

## Spaced repetition

Track student familiarity with important facts/clues and revisit weak material automatically.

Ideally, the system eventually distinguishes knowledge such as:

```text
Frankenstein -> Mary Shelley          mastered
Frankenstein -> Victor Frankenstein   mastered
Frankenstein -> Robert Walton          learning
Frankenstein -> Ingolstadt             weak
Frankenstein -> De Lacey family        unseen
```

Important clues should be reviewed more aggressively than obscure ones.

---

# Student specialization and progress

Students will generally concentrate on one broad specialty.

The interface should help each student see their "study universe" becoming more complete over time.

Example concept:

```text
HISTORY

Mastered       347 topics
Learning       122 topics
Unseen         891 topics

US Presidents             72%
US Wars                   61%
Ancient History           38%
European Monarchs         24%
Revolutions               53%
World War II              81%
```

Avoid fake precision in mastery calculations. The exact progress model should be evidence-based and understandable.

---

# Data storage direction

A specialized graph database is probably unnecessary initially.

A relational database such as PostgreSQL is likely sufficient, with tables conceptually resembling:

```text
topics
aliases
facts / relationships
questions
question_clues / question_fact_evidence
student_progress
```

Do not lock into this schema until you inspect the corpus and current repository.

A graph-shaped domain model can still be represented cleanly in relational tables.

---

# AI / data-processing pipeline

The likely processing model is multiple deliberate passes rather than one enormous prompt.

Conceptually:

```text
CSV question files
      |
      v
Question parser / normalizer
      |
      +-- canonical answer
      +-- category/subcategory
      +-- question structure
      +-- clue spans
      +-- named entities/concepts
      |
      v
Entity/topic resolver
      |
      +-- aliases and variants collapse to stable topic IDs
      |
      v
Fact / relationship extractor
      |
      v
Topic aggregator
      |
      v
Importance / difficulty analysis
      |
      v
Study-summary generation
      |
      v
Validation / QA
      |
      v
Quiz-bowl knowledge base
```

Design this pipeline so that intermediate artifacts can be inspected, rerun, corrected, and regenerated.

Avoid a black-box workflow where thousands of questions go into an LLM and a finished database comes out with no provenance.

---

# CRITICAL: inspect the CSV files without exhausting context

The question files are large. **Do not read entire CSV files into the model context.**

You may use scripts and command-line tools to inspect and summarize them programmatically.

A good investigation sequence would be:

1. List the relevant files and record sizes.
2. Detect encoding, delimiter, header structure, and quoting conventions.
3. Read headers only.
4. Use a script to compute row counts and basic column statistics.
5. Sample a small number of rows from each file.
6. Sample from the beginning, middle, and end rather than assuming the first rows are representative.
7. Randomly sample additional rows with a fixed seed so findings are reproducible.
8. Compute distinct/value-frequency summaries for likely metadata columns without dumping all values into context.
9. Measure missing/null fields.
10. Look for differences in schema among files.
11. Look for duplicate or near-duplicate questions/answers.
12. Identify whether tossups, bonuses, packets, rounds, difficulty, categories, answer lines, notes, or clue segmentation are represented.
13. Determine how answer formatting works, including alternate acceptable answers, prompts, pronunciation notes, bracketed text, etc.
14. Determine whether a question's clue order is recoverable from the source text.
15. Inspect enough representative examples from every major category to understand writing style and complexity.

Write small inspection scripts if useful and keep them in a sensible project location if they may have lasting value.

Prefer outputs like:

```text
file_a.csv
  rows: 2,134
  columns: 7
  category counts:
    Literature: 421
    History: 389
    ...
  missing answer: 0
  missing category: 17
```

rather than printing hundreds or thousands of source rows.

When you need examples, pull only a focused sample into context.

If you use Python/pandas or another CSV library, be defensive about malformed lines, quoting, encoding, embedded newlines, and unexpectedly large fields.

Do not mutate the original source CSVs during inspection.

---

# Questions to answer during the initial data investigation

Use the real dataset to refine this architecture. At minimum, determine:

- What is the schema of each CSV file?
- Are all files from the same source/export format?
- What does one logical question look like?
- Are there tossups, bonuses, or other formats?
- Are answers clean enough to identify canonical topics directly?
- How are alternate answers represented?
- How reliable are existing categories?
- What category taxonomy is present?
- Is question difficulty represented explicitly or inferable?
- Are clues ordered from hard to easy as traditional tossups generally are?
- Are clue boundaries explicit, or must they be inferred from sentences/clauses?
- Are questions duplicated across sets?
- Are there obvious formatting artifacts that need normalization?
- What proportion of answers correspond cleanly to one topic versus lists, multi-part answers, formulas, dates, quotations, etc.?
- Which domain concepts require special handling?
- Is there enough information to distinguish question metadata from question text reliably?
- What should be stored verbatim for provenance?
- What preprocessing can be deterministic and done without an LLM?
- Which steps genuinely require LLM inference?
- Where should validation/human review occur?
- How can processing be chunked, checkpointed, and resumed without repeating expensive work?

Also look for important realities that this handoff document did not anticipate.

---

# Be conservative about LLM usage

Use deterministic parsing, SQL, Python, regexes, statistics, and ordinary software wherever they are sufficient.

Reserve LLM calls for tasks that genuinely require semantic understanding, such as:

- entity/topic identification,
- alias resolution when deterministic matching is inadequate,
- semantic clue extraction,
- relationship extraction,
- concise study-summary generation,
- generating pedagogically useful recall questions,
- classification when existing metadata is insufficient.

Plan for model outputs to occasionally be wrong.

Prefer structured outputs with schemas and validation.

Keep prompts small and focused. Avoid feeding the entire corpus, entire large files, or unnecessarily large groups of questions to a model at once.

Cache outputs and design processing to be resumable.

---

# Provenance and auditability

This is important.

Whenever AI derives a fact or association from the corpus, preserve enough provenance to answer:

> Why does this information exist in the study database?

A fact may point to one or more source question IDs and ideally the supporting clue text or span.

This will make it much easier to:

- inspect hallucinations,
- resolve contradictory facts,
- tune extraction,
- regenerate summaries,
- and build admin/review tools later.

Never silently overwrite source data with AI-normalized versions.

---

# Entity resolution / canonicalization

Expect this to be a substantial problem.

Examples such as:

```text
FDR
Franklin Roosevelt
Franklin D. Roosevelt
President Roosevelt
```

may refer to the same topic.

Likewise, answer lines may contain formatting conventions that distinguish required answer text from accepted variants.

Do not assume exact string equality is enough, and do not indiscriminately merge semantically similar answers.

The final architecture should provide:

- stable IDs,
- canonical display names,
- aliases,
- source answer strings,
- and a way to correct incorrect merges/splits.

Determine the actual answer-line conventions from the CSVs before designing the resolver.

---

# Possible derived corpus features

Once the data is understood, consider computing reusable deterministic features such as:

- normalized answer forms,
- answer frequency,
- category and subcategory distributions,
- duplicate hashes,
- sentence/clause positions within tossups,
- source file / packet / round identifiers,
- approximate clue position percentages,
- token/word counts,
- repeated n-grams or phrases associated with an answer,
- entities recurring across questions,
- question similarity or clustering signals.

These can later help the AI extraction pipeline and reduce model cost.

---

# Product principles

Keep these principles in mind as you refine the design:

1. **Recognition over exhaustive scholarship.**
   Students need high-yield associations that lead to correct buzzes.

2. **Breadth before depth.**
   A beginner knowing the essential clues for 1,000 topics is generally more useful here than knowing every obscure clue for 50.

3. **Corpus-grounded curriculum.**
   Let actual quiz-bowl questions strongly influence what receives study priority.

4. **Structured knowledge before prose.**
   Summaries should be generated from an inspectable knowledge model where possible.

5. **Every AI assertion should be correctable.**
   The system must tolerate extraction mistakes without requiring a rebuild from scratch.

6. **Provenance matters.**
   Keep links back to source questions.

7. **Incremental, resumable processing.**
   A failed batch should not invalidate hours of earlier work.

8. **Do not waste model context.**
   Analyze large datasets programmatically and bring only targeted evidence into the agent context.

9. **Optimize for actual student use.**
   Avoid an elaborate ontology that does not improve studying or training.

10. **The source CSVs are immutable inputs.**
    Normalize into derived files/database tables rather than editing the originals.

---

# Your immediate tasks

## 1. Inspect the repository

Understand the existing folder layout, source data files, code (if any), config, and documentation.

Do not make broad architectural assumptions until this is done.

## 2. Inspect the question data safely

Follow the large-file strategy above.

Produce concise internal notes or a repository document summarizing:

- schemas,
- file differences,
- row counts,
- category distributions,
- representative examples,
- answer conventions,
- anomalies,
- implications for the architecture.

Do not create giant dumps of the CSV contents.

## 3. Refine the architecture

Using what you learn from the actual data, decide how the concepts in this document should change.

Pay particular attention to:

- source-question model,
- canonical answer/topic model,
- clues/facts/relationships,
- categories,
- topic templates,
- extraction pipeline,
- provenance,
- difficulty/importance inference,
- data validation,
- resumable processing,
- likely database schema.

## 4. Create `AGENTS.md`

Create an `AGENTS.md` in the project root for all future agents.

It should be concise enough to remain useful but detailed enough that a fresh agent can work safely without rediscovering the project's fundamental decisions.

Include at least:

- project purpose and pedagogical goal,
- repository structure,
- description of the source datasets,
- important data conventions discovered during inspection,
- architectural overview,
- important domain terminology,
- data-processing pipeline,
- rules for handling the large CSV files,
- provenance requirements,
- canonicalization/entity-resolution approach,
- coding and testing conventions discovered or established,
- commands for common development/test/data tasks,
- files/directories that are generated versus source-controlled,
- safety rules for preserving original data,
- current implementation status,
- unresolved design questions / TODOs,
- instructions for keeping `AGENTS.md` current when architecture or workflows change.

`AGENTS.md` should reflect **what is actually true in the repository after your investigation**, not merely copy this handoff document.

## 5. Recommend the first implementation phase

After investigating, outline a practical first implementation phase that operates on the full dataset but builds the system incrementally.

For example, a sensible sequence might be:

```text
raw imports
-> deterministic normalization
-> stable question IDs
-> answer parsing
-> duplicate detection
-> topic/entity extraction
-> entity resolution
-> clue/fact extraction
-> aggregate topic records
-> scoring/importance
-> summaries
-> training UI
```

But modify that ordering if the corpus suggests something better.

Prefer building reusable ingestion and inspection infrastructure before launching thousands of expensive model calls.

---

# Important non-goals for the first pass

Do not prematurely spend effort on:

- polished visual design,
- elaborate animations,
- a perfect ontology,
- exotic infrastructure,
- microservices,
- a graph database solely because this is called a knowledge graph,
- calling an LLM on every row before determining what deterministic preprocessing can accomplish.

The early priority is creating a trustworthy transformation from the existing question corpus into a structured, inspectable curriculum.

---

# Expected mindset

Act as both a software engineer and a data-modeling/product-design partner.

The user has chosen to process the full corpus rather than run a tiny proof-of-concept, but that does **not** mean everything must be processed in one monolithic operation. Work against the full dataset using small, inspectable, resumable batches and aggregate statistics.

When the real data conflicts with an assumption in this document, trust the data and record the revised decision in `AGENTS.md`.

The key question behind every architectural choice is:

> Will this help a student build a larger, faster network of useful quiz-bowl recognition knowledge?

