# Telestics and source highlighting — 4 November 2026

Rebuilt from default-branch commit `87654bd392e5f287c4e06d877fc9f72860fdc64d`
and the same pinned source repositories. The new snapshot contains **54,564
letter-pattern candidates**: 27,471 preserved acrostics and **27,093 telestics**
(13,749 forward, 13,344 reverse). All **27 isopsephy results** remain unchanged.
There are **113,571 passage lines**, including every previous passage unchanged.

Position `-1` selects the final normalized Greek letter. Its frequencies were
calculated independently from all 253,313 eligible lines in the fresh full run;
second-from-end searching is rejected. The import retains all 732 editions,
260,885 line records, and 2,045 ingest decisions (732 included, 1,309 without
verse, four pre-existing rejected files). The dictionary retains 83,891 included
word forms. No parser, normalization, or numerical-value rules changed.

The public and local viewers show each source line once, highlighting the
selected source letter with its original accents. The public Γ/L filter also
supports telestics at the last word on the ending line of the vertical reading:
bottom forward, top reverse. It finds **583 three-letter suffix matches**, of
which **four are whole-word matches**. The existing initial-letter Γ/L set is
unchanged (112 three-letter, five whole-word). Matching horizontal letters and
vertical corner letters are marked in the source text.

Validation evidence:

- `output/telestics-run.txt`: complete frequency/search/isopsephy run counts.
- `output/telestics-comparison.json`: exact preservation of all old result rows,
  scores, passages, edition metadata, frequencies and ingest/isopsephy audits;
  independent final-letter counts and scores; complete snapshot export.
- `output/corpus-verification.json`: all 54,564 reading paths and known examples.
- `output/telestics-tests.txt`: Python/Node checks, including source mapping on
  every published passage and static query parity for the new position and Γ/L.
- `output/telestics-browser.json`: desktop/mobile browser checks of both viewers,
  both telestic directions, Γ/L modes, text preservation, filters, scores,
  existing acrostics/isopsephy, loading failures, and layout.

The committed snapshot is ready for the normal Pages publication on merge.
Pull requests now run the build/test workflow without deploying. Results retain
the existing corpus/boundary limitations and are candidates, not evidence of
intention. The earlier reports below are historical evidence.

# Source-structure corrections — 1 November 2026

The 1 November snapshot contained **27,471 acrostic candidates**, **27 isopsephy
results** (23 two-line-group, 4 individual-line), and **71,790 passage lines**.
It was rebuilt from the same pinned XML sources, with every Greek reading
unchanged. The original full database and Mini viewer were preserved.

AP 7.548's two XML line elements containing only speaker labels remain in the
full database with original ordinals, citations, raw labels, and the explicit
`speaker_label_only` flag. They no longer count as metrical verses. All original
adjacencies are checked, including those through labels, so genuine numbering
gaps, missing XML lines, and unit boundaries still stop searches.

The source edition `tlg7000.tlg001.perseus-grc6` calls its numbered book/chapter
units epigrams in its CTS citation declaration. The parser now recognizes those
815 units only for that exact edition, declaration, and hierarchy. Original
`chapter` kinds remain in provenance. Arbitrary chapters are not treated as poems.

| Newly recovered poem | Group size | Iota policy | Equal group total |
|---|---:|---|---:|
| AP 6.321 | 2 | Count only | 5,699 |
| AP 6.324 | 2 | Count only | 9,117 |
| AP 6.325 | 2 | Both | 5,953 |
| AP 6.326 | 2 | Both | 5,982 |
| AP 6.327 | 1 | Both | 4,111 |
| AP 6.329 | 2 | Count only | 7,579 |
| AP 7.548 | 2 | Omit only | 7,150 |

AP 7.548 retains Paton's `Δαίμων`; its counted totals are 7,160 / 7,150.
These policy labels describe this selected text, not an inference about ancient
orthographic practice. AP 7.549 and 7.550 remain unequal and are not emended.
AP 7.547 remains count-only at 7,267 per couplet.

One acrostic is added: forward second-letter **ΙΣΧΕ**, AP 7.548's actual verse
citations 2, 3, 5, 6. Its log2 score is 18.24345200079907. Direction/position
counts are now 5,202 / 5,161 / 8,549 / 8,559 (forward1/reverse1/forward2/reverse2).

The exhaustive comparison preserves all 27,470 previous acrostics and all 20
previous isopsephy results exactly, including scores and totals. Edition source
hashes, dictionary, positional frequencies, denominators, and ingestion logs
are unchanged. All 260,885 source line records retain their raw/selected text,
citations, ordinals, units, and damage flags. Only 4,964 poem associations and
the two speaker flags change. The full run now recognizes 4,414 poem units.
Among existing audits, 7.548 changes from skipped to tested; AP 15.22 remains
skipped, with the more specific unit-boundary reason replacing its numbering
discontinuity reason. No previously tested poem becomes excluded.

`output/structure-fix-comparison.json` records exact old/new database SHA-256
hashes, every result addition, and audit transitions. The baseline commit is
`726b30e6533906d7a691aa3f01a80078015f0a89`; it is also the rollback reference.
`output/structure-fix-run.txt` records the complete processing commands.
`tests/compare_structure_fix.py` reproduces the exhaustive read-only comparison;
`tests/verify_corpus.py` validates all 27,471 reading paths and known examples.

The 31-test suite includes source-derived positive fixtures and negative cases
for malformed/empty speaker labels, real empty/damaged lines, fragment markers,
numeric/XML gaps, nested boundaries, inline labels, incorrect editions and
citation declarations, wrong chapter hierarchy, and prose chapters. Static
export parity checks compare every published result and passage with SQLite.
Independent review also recomputed the target totals and compared source bytes,
existing results, and database hashes. Headless Chromium checks passed for all
recovered poems, their policies/totals and original citations, ΙΣΧΕ, the existing
known examples, combined filters, sorts, pagination, keyboard selection, and
loading/error recovery. Desktop and 390-pixel mobile screenshots were inspected;
there is no horizontal overflow or JavaScript error. See
`output/structure-fix-browser.json`.

The report below describes the earlier baseline and retains its historical
counts and comparisons. It does not describe the current published snapshot.

# Historical reproduction and validation — 8 October 2026

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
AP8.39 display payload, and query safety/read-only enforcement), a direction-menu
markup regression test, and all 12 core fixture tests pass: 17 total.
`node --check viewer/app.js` and live local HTTP checks also pass.

A subsequent explicitly requested headless check found and fixed the malformed
Forward menu option. Screenshot inspection also led to wider mobile controls.
A third additive Git commit records these fixes; the baseline and first viewer
commits are unchanged. The supported computer-use route was blocked (in-app
browser unavailable, browser inventory empty, native app discovery reporting the
Mac locked). Existing Playwright with cached Chromium 153.0.8010.12 successfully
ran in a fresh headless context with its sandbox enabled. It never unlocked or
reused the desktop session.

Desktop 1365 px and mobile 390 px rendering and screenshots were verified.
Checks cover initial counts, 50-row pagination, score sorting, accented Greek
search, direction/position filters, forward and reverse highlighted paths,
empty results, AP8.39 with both iota conventions, mobile passage selection,
absence of horizontal overflow, and absence of JavaScript errors. Evidence is
in `output/headless/`; `tests/headless_viewer.cjs` is an optional development
check requiring an existing Playwright installation. No scanner or database
recomputation was needed; no remaining visual QA blocker applies to these two
headless viewport checks. Native unlocked-desktop testing was not performed.
