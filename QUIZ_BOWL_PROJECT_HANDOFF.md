# Quiz Bowl Training Platform — Project Vision

## Purpose and audience

Build a training website that helps middle- and high-school quiz-bowl students develop broad recognition knowledge: the facts and associations that let them identify answers early in a question.

Students typically specialize in literature, math/science, history, or sports/media/miscellaneous. The curriculum favors essential knowledge across many topics before deeper study of a few. A literature specialist, for example, can recognize *Frankenstein* through Mary Shelley, Victor Frankenstein, Robert Walton, or “The Modern Prometheus” without first reading the entire novel.

Students can select their practice level. Middle-school practice defaults to middle-school material; high-school practice defaults to both middle- and high-school material. Topics can appear in either or both sets, with study content reflecting the selected levels.

## Learning experience

The website combines a concise, interconnected wiki with a retrieval-practice and spaced-repetition trainer.

**Topic pages** organize people, works, events, places, scientific concepts, and other recurring answers. Each page provides a concise study summary, accepted names and aliases, useful facts, recognition clues, related topics, and supporting source questions. Fields suit the topic: a novel has an author, characters, and plot clues; an event has dates, participants, and outcomes; a scientific concept has definitions, mechanisms, and formulas. Topics can belong to multiple categories.

**Quick recall** offers focused questions after study, such as “Who wrote Frankenstein?” or “Who creates the creature?” A topic page supports a “Quiz me on this topic” action.

**Buzz practice** progressively reveals tossup clues and rewards earlier correct answers. Feedback helps students identify which clues they recognized or missed.

**Bonus practice** preserves each lead-in and its three ordered questions as a contextual unit. Later parts can depend on the lead-in and earlier parts.

**Spaced repetition** revisits weak facts and clues, with more attention to high-value material. Progress can distinguish knowing Frankenstein’s author from recognizing Robert Walton or Ingolstadt.

**Specialty progress** shows mastered, learning, and unseen material across topics and subcategories. Progress measures reflect demonstrated learning and remain understandable to students.

## Curriculum grounded in competition

The question corpus provides evidence for what students should learn. Recurring answers, repeated clues, and appearances across tournaments help establish study priorities. Repeated question occurrences retain value as evidence of competition frequency.

Recognition clues are central to the curriculum: “Modern Prometheus” points to *Frankenstein*, and “Emancipation Proclamation” points to Abraham Lincoln. Useful priority signals include recurrence, breadth across sources, clue position, and how distinctly a clue identifies its answer.

Clues may be organized into essential, competitive, and deeper recognition tiers. These describe learning depth separately from middle- or high-school set membership. The emphasis remains breadth of essential recognition before obscure detail.

## Knowledge model

The product has three connected layers:

1. **Question bank:** source questions, answers, tournament context, and school-level membership. Tossups retain their clue order; bonuses retain their lead-in and three parts.
2. **Knowledge base:** topics, aliases, structured facts, relationships, and recognition clues supported by source evidence. Wiki links connect related topics, such as Mary Shelley and *Frankenstein*.
3. **Training engine:** study pages, recall questions, buzz and bonus practice, spaced repetition, and student progress.

Structured knowledge supports summaries and practice material. For example, the relationship “Mary Shelley wrote Frankenstein” can support a topic field, a wiki link, and a recall question. Alternate names connect to the same topic where appropriate, while ambiguous answers remain distinguishable.

Facts and clues remain traceable to supporting questions and correctable when errors are found. Source context matters, especially for historical or time-sensitive statements. Reliable evidence and transparent corrections make the curriculum trustworthy.

## Product principles

- **Recognition:** teach associations that help students answer accurately and buzz earlier.
- **Breadth:** prioritize essential clues across a large study universe.
- **Relevance:** use actual competition material and the student’s chosen levels to guide study.
- **Connected knowledge:** make relationships between topics easy to explore and recall.
- **Trust:** ground study content in inspectable evidence and support corrections.
- **Practical learning:** judge features by whether they improve students’ recognition, retention, and confidence.
