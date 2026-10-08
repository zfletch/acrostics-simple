# Reproduction and validation — 8 October 2026

The six scripts ran locally against the original Python project's pinned corpus
commits. No model scan, paid service, public upload, GitHub push or deployment
was used. The original research bundle and Claude source were read only.

## Acrostics

| Direction | Position | New matches | Historical rules | Shared matches |
|---|---:|---:|---:|---:|
| Forward | 1 | 5,202 | 6,255 | 5,197 |
| Reverse | 1 | 5,161 | 6,203 | 5,151 |
| Forward | 2 | 8,548 | 10,041 | 8,531 |
| Reverse | 2 | 8,559 | 10,037 | 8,544 |

**27,470** new candidates total. The first three historical-rule replays match
every archived candidate key exactly. The last row is an independent replay of
the historical rules on the frozen historical inputs: there is no archived
reverse-position-2 table, and it is not claimed as historical verification.
`output/candidate-differences.json` records every added/removed candidate and
its first applicable explanation. No removal or addition is unexplained.

The major reductions come from stopping at unnumbered/quotation boundaries,
rejecting split or unusable lines, enforcing numbering continuity, and recounting
the dictionary after editorial cleaning. A few changed readings or glyph
normalizations add matches. The old heuristic score is deliberately not compared
to the new score: the user explicitly replaced its context/boundary/length and
document-frequency factors with the reciprocal positional-frequency product.
All 27,470 new log scores were independently checked against the direct product.

Known text checks reproduce ΛΕΠΤΗ at Aratus 783–787, reverse ΕΚΤΩΡ at Iliad
6.511–515, and second-letter ΕΛΛΗΝΕΣ at Quintus 7.502–508. These checks establish
reading paths, not intentionality or novelty.

## Corpus, dictionary and denominators

The import records 732 editions and 260,885 XML line records. Of those editions,
29 have zero usable lines. There are 253,313 usable position-1 lines; position 2
has 253,164, excluding 149 short lines. A further 7,572 line records are unusable:
4,576 split pieces, 2,995 without usable Greek, and one nested-line structure.
Verse inside excluded editorial containers is not in this line table. Four
files are rejected for lacking the supported single-edition structure; this is
logged, not silently repaired. See `ingest_log` and the README's scope rules.

The new dictionary stores 178,761 distinct forms across all lengths; **83,891**
meet the chosen length 4–12 / frequency ≥2 filters. The historical dictionary
stores **173,680 forms already restricted to length 4–12**, of which 84,554 meet
the frequency threshold. Its stored lines contain 182,583 distinct forms and
1,579,543 tokens across all lengths. This distinction corrects the initial
assumption that its word_forms table contained every token length.

990 formerly eligible words fail the new recount and 327 become eligible.
No lexical items were handpicked for inclusion. All available encoded Greek
verse in the two pinned repositories is considered; this is not the entirety
of surviving Greek literature or a corpus-wide prose-word frequency model.

## Genuine whole-poem isopsephy search

There are 3,599 explicitly encoded poem/epigram units. The group-size-2 search
tests 2,431 whole poems and finds **17** equal successive line-pair totals.
The group-size-1 search tests 3,447 whole poems and finds **3** poems whose
individual line totals all agree. All 20 hits in this run are in the Greek
Anthology; that is an observed result, not an anthology-only search filter.

The two-line-group hits are AP 7.547, 7.668, 8.39, 9.12, 9.80, 9.123,
9.344, 9.345, 9.350, 9.351, 9.353, 9.354, 11.70, 11.87, 11.187,
11.199 and 12.20. Individual-line hits are AP 7.675, 9.348 and 13.31.
The database retains attribution, edition, original passages, both sets of line
sums and group sums. These are numerical matches requiring scholarly review;
there is no claim of discovery, intention, chronology or statistical significance.

Skipped group-size-2 units: 1,055 ineligible line counts, 45 explicit gaps/damage,
29 unsupported alphabetic characters, 20 prose paragraphs, 16 uncertain or
incomplete lines, and 3 numbering discontinuities. Group-size-1 exclusions are
38, 45, 30, 20, 16 and 3 respectively. The full per-poem audit is in SQL.
Poems without explicit `poem`/`epigram` boundaries are not counted in this universe.

AP 8.39 is found through the same loop as every other poem. Its sums are:

| Iota convention | Lines 1–2 | Lines 3–4 |
|---|---:|---:|
| Omit subscript | 6,903 | 6,903 |
| Count subscript | 6,903 | 6,913 |

The difference is the iota in `νηῷ`. Ordinary written iota is never omitted.
The source XML hash agrees with the latest independent AP8.39 reproduction.

## The remembered Helen-related candidate

A plausible lead is **ΕΡΑΣΑΙ**, second letters in Euripides, *Helen* 3–8,
historical fixed-column candidate **1255**. The new scan retains it:

| Line | Opening | Second letter |
|---:|---|:---:|
| 3 | λευκῆς | Ε |
| 4 | Πρωτεὺς | Ρ |
| 5 | Φάρον | Α |
| 6 | ὃς | Σ |
| 7 | Ψαμάθην | Α |
| 8 | τίκτει | Ι |

Other leads: **ΕΛΕΝΑ** at Nonnus, *Dionysiaca* 8.113–117 (old id 6341),
and the separately reported **ΕΛΛΗΝΕΣ** (“Greeks”) at Quintus 7.502–508
(old id 7518). ΕΛΛΗΝΕΣ is not Helen's name. No available note establishes
which candidate the user remembers. No identity or literary significance is
asserted from the recollection. `output/helen-leads.json` preserves exact rows.

## Tests and delivery

12 independent, hand-sized fixture tests pass. They cover NFD and spacing iota,
sigma folding, traditional numerical signs and elision punctuation, forward and
reverse direction, a manually calculable score, position 2, short lines,
edition/unit/sequence/numbering barriers, editorial choices and note exclusion,
split lines, unrelated DB protection, a new numerical fixture, whole-poem versus
window equality, and the AP8.39 arithmetic.

`tests/verify_corpus.py` verifies all 27,470 reading paths and four known corpus
examples. SQLite integrity checks pass and the full database has no foreign-key
violations. The portable results database contains 71,764 referenced line
records and is about 20 MB before compression. It is committed with the source;
the larger full corpus database and downloaded repositories remain local and
are excluded from Git and the compact bundle. `schema.sql` documents the full DB.

The first local Git commit contains this working scanner baseline and SQL
outputs. A separate second commit adds the local viewer and its tests
and documentation. No remote is configured for the simplified project.


The viewer's four database behavior tests (search/filter, sort/pagination,
AP8.39 display payload, and query safety/read-only enforcement) pass alongside
all 12 core fixture tests, for 16 total. `node --check viewer/app.js` also passes.
Live local HTTP endpoints are checked separately. The only outstanding QA limit
is visual browser inspection: the Mini was locked, automatic unlock failed, and
the computer-use tool reported no available browser. No existing browser tab was
changed. This is a visual validation limit, not a scanner or SQLite blocker.
