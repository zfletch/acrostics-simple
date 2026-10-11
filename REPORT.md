# Results and validation

The included snapshot uses the two exact corpus revisions listed in the README,
dictionary lengths 4–12, minimum token frequency 2, letter positions 1 and 2 in
both directions, and isopsephy group sizes 2 and 1. All processing uses the
Python standard library and local SQLite databases.

## Acrostics

| Direction | Position | Candidates |
|---|---:|---:|
| Forward | 1 | 5,202 |
| Reverse | 1 | 5,161 |
| Forward | 2 | 8,548 |
| Reverse | 2 | 8,559 |

There are **27,470** candidates. Scores are the logarithm of the reciprocal
positional-frequency product. Every score is independently checked against the
direct product by `tests/verify_corpus.py`. Longer words and rarer letters score
higher; the score is not a significance test or evidence of intention.

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

The dictionary stores 178,761 distinct forms across all lengths; **83,891**
meet the length 4–12 / frequency ≥2 filters. No lexical items are handpicked for
inclusion. All available encoded Greek verse in the two pinned repositories
is considered; this is not the entirety of surviving Greek literature or a
corpus-wide prose-word frequency model. Alternate editions remain in the corpus
and can increase both token and letter counts.

## Whole-poem isopsephy search

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
The exact edition, source revision and XML SHA-256 are recorded in
`provenance/source-attribution.json`; `provenance/ap8-source.xml` retains its
source TEI header and attribution.

## Inspecting a positional match

**ΕΡΑΣΑΙ** is formed by the second letters in Euripides, *Helen* 3–8:

| Line | Opening | Second letter |
|---:|---|:---:|
| 3 | λευκῆς | Ε |
| 4 | Πρωτεὺς | Ρ |
| 5 | Φάρον | Α |
| 6 | ὃς | Σ |
| 7 | Ψαμάθην | Α |
| 8 | τίκτει | Ι |

The source is `urn:cts:greekLit:tlg0006.tlg014.perseus-grc2`. This example is
also a viewer fixture; its presence establishes a reading path, not literary
significance. Search for ΕΡΑΣΑΙ and select forward direction, position 2 to
inspect it in context.

## Reproducibility checks

The fixture suite covers NFD and spacing iota, sigma folding, traditional
numerical signs and elision punctuation, forward/reverse directions and manually
calculable scores, second letters, short lines, edition/unit/sequence/numbering
barriers, TEI choices and note exclusion, split lines, unrelated-database
protection, whole-poem equality, and AP 8.39 arithmetic. Viewer tests cover
filtering, ordering, pagination, the direction menu and read-only queries.

The full processing database has 71,764 line records referenced by results.
The included compact snapshot stores these passages, all result rows, edition
hashes, frequencies, ingestion and isopsephy audits, and source metadata. It is
about 20 MB. The larger full processing database and downloaded repositories
are excluded from Git. `output/schema.sql` documents the full database.

Validation commands and optional browser setup are in the README. See
`output/run.log`, `output/corpus-verification.json`, `output/tests.txt` and
`output/headless/result.json` for recorded evidence.
