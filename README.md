# Greek acrostics and isopsephy

Six small Python command-line scripts, one shared text helper, SQLite output,
and no third-party Python dependencies. Requires Python 3.9+ and Git. Everything runs locally.

## Browse the included results

Clone the repository:

```sh
git clone https://github.com/zfletch/acrostics-simple.git
cd acrostics-simple
python3 viewer.py
# Open http://127.0.0.1:8766 in a browser on this computer; Ctrl-C stops it.
```

Python 3.9+ is enough to run the viewer. No corpus download, database rebuild,
package installation, or external web service is needed. The included
`output/results.sqlite3` contains 27,470 acrostic candidates, 20 whole-poem
isopsephy matches, and their passages. The viewer stays on the local computer.

## Reproduce a scan

Run these commands from the repository directory. Python uses only its standard
library, so there are no third-party Python packages to install. Python 3.9.6
was used for the included results; Python 3.9+ is supported. Downloading the
pinned source repositories requires Git and network access; subsequent processing
runs locally. An optional virtual environment keeps the run isolated:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 download_corpora.py
python3 build_dictionary.py --database output/new-run.sqlite3 \
  --min-length 4 --max-length 12 --min-frequency 2
python3 calculate_frequencies.py --database output/new-run.sqlite3 --position 1
python3 calculate_frequencies.py --database output/new-run.sqlite3 --position 2
python3 search_forward.py --database output/new-run.sqlite3 --position 1
python3 search_reverse.py --database output/new-run.sqlite3 --position 1
python3 search_forward.py --database output/new-run.sqlite3 --position 2
python3 search_reverse.py --database output/new-run.sqlite3 --position 2
python3 search_isopsephy.py --database output/new-run.sqlite3 --group-size 2
python3 search_isopsephy.py --database output/new-run.sqlite3 --group-size 1
python3 tests/verify_corpus.py --database output/new-run.sqlite3
python3 -m unittest discover -s tests -v
```

A fresh clone includes `output/results.sqlite3`, a compact results snapshot.
The commands above create a separate full processing database at
`output/new-run.sqlite3`. To reuse already downloaded corpora, pass their parent
directory to both `download_corpora.py --destination /path/to/corpora` and
`build_dictionary.py --corpora /path/to/corpora`. The two named checkouts must
be clean and at the exact revisions below. The downloader verifies existing
checkouts without fetching them again; it refuses mismatched or modified sources.

The builder refuses an existing output filename; use a fresh filename for each
rebuild. The other five processing commands only
accept this project's full processing database format. Searches replace only
results for their own direction/position or group size. Recalculating a frequency
position removes that position's existing acrostic scores; rerun both searches afterwards.
Any positive position is accepted; a line shorter than that position breaks a
window, and a frequency calculation with no eligible lines stops with an error.

```sh
sqlite3 -header -column output/new-run.sqlite3 \
  "SELECT word,author,title,start_citation,end_citation,log2_score
   FROM acrostic_results WHERE direction='reverse' AND position=1
   ORDER BY log2_score DESC,word,edition_id,start_sequence LIMIT 20;"
sqlite3 -header -column output/new-run.sqlite3 \
  "SELECT author,citation,group_size,convention,omit_totals,count_totals
   FROM isopsephy_results ORDER BY urn,citation,group_size;"
```

`output/results.sqlite3` is a smaller read-only-results snapshot, with the same
result-view column names materialized as tables and a `passages` table. It omits
the full corpus and dictionary. `output/schema.sql` is the processing DB schema.
The optional SQL examples above require the `sqlite3` command-line client. To query the included snapshot instead,
replace `output/new-run.sqlite3` with `output/results.sqlite3` in those queries.

Downloaded `corpora/`, generated full databases (`output/research.sqlite3` and
`output/new-*.sqlite3`), SQLite temporary files, Python caches, and local ZIP
bundles are excluded by `.gitignore`. Source scripts, the viewer, the compact
snapshot, provenance and validation evidence are tracked.

## The six scripts

| File | Job |
|---|---|
| `download_corpora.py` | Download two exact commits, check them out detached, and record them. Reuse only clean, exact existing checkouts. |
| `build_dictionary.py` | Read TEI once, store source text and boundaries, count normalized word forms and edition frequencies. |
| `calculate_frequencies.py` | Count empirical Greek letters at the requested one-based position. |
| `search_forward.py` | Read that letter top-to-bottom across consecutive lines; keep dictionary matches. |
| `search_reverse.py` | Read the same letter bottom-to-top; keep dictionary matches. |
| `search_isopsephy.py` | Compare sums of successive equal-size groups across an entire explicitly encoded poem. |

`corpus.py` is the deliberate shared helper: all tasks must agree on Unicode,
TEI reading, and boundaries. It also contains a small guard against writing to
an unrelated database. The forward and reverse loops are intentionally separate
and nearly identical so either can be read without a search framework.
`build_dictionary.py` imports the repository pins from the downloader; there is
one authoritative list of revisions. Supporting verification scripts live in
`tests/`; source evidence and outputs are separate from the six entry points.

## Exact corpus scope and provenance

The corpus revisions are pinned in `download_corpora.py` and recorded in each
processing database’s `metadata`:

| Repository | Commit |
|---|---|
| https://github.com/PerseusDL/canonical-greekLit | `790c84289edbdbe289dd7b752bfea29f0af4299d` |
| https://github.com/OpenGreekAndLatin/First1KGreek | `4c9c843d80ee94b4371f52add5f7d68bbfe7ba4c` |

Scope is **all available encoded Greek verse lines in those snapshots**, including
verse quoted in prose, alternate editions, and repository subdirectories. It is
not all surviving Greek literature, and it is not the prose token population.
Files must have an `.xml` extension and contain `-grc` or `.grc` in the filename.
Perseus is read first, then First1K, sorted within each; a repeated edition URN
is kept once.
Different edition URNs remain separate. No poet, period, genre, primary-edition,
minimum-work-size, or score selection is imposed. An edition with no eligible
letters may remain in the audit but contributes zero to the frequency denominator.

Repository commits, edition paths and SHA-256 hashes are in the database and
`provenance/`. Each line has an edition id, original XML `<l>` ordinal,
citation, unit, optional explicit poem id, original text, chosen reading, and
eligibility flags. `ingest_log` records included, empty, duplicate or rejected files.
The repositories retain their upstream licensing notices; excerpts/results retain
source attribution. The compact distribution does not redistribute both repositories.

## Text and boundary rules

* Strict standard-library XML parsing; no silently recovered malformed XML.
* Use one edition division. Exclude verse inside notes, deleted material and
  other listed editorial containers. In a line, select `lem` for apparatus and
  `corr`, then `reg`, then `expan` for choices. A choice without a supported
  reading makes the line unusable. Empty milestones retain following text.
* Every encoded `div` and quotation container has its own unique boundary,
  including unnumbered divisions and repeated labels. This conservatively
  splits stanzas, dramatic sections and layout divisions too. It can miss
  patterns spanning them; results are restricted to the encoded units.
* Keep blank/unusable line records as barriers. Reject split-line pieces marked
  `I`, `M`, or `F` instead of pretending that each is a complete metrical line.
  Do not merge fragments or repair the text. Nested line structures are excluded.
* A candidate must use consecutive XML ordinals within one edition and unit.
  Explicit consecutive numeric line labels must also increase by one. A gap or
  duplicated number breaks the candidate. Unknown/non-numeric labels are retained;
  no claim is made to reconstruct missing ancient lineation.
* Normalize with Unicode NFD **before** uppercasing. Remove accents, breathings,
  diaeresis and subscript iota (`U+0345` and spacing `U+1FBE`). Retain ordinary
  written iota. Fold final/lunate sigma and Greek glyph variants. Count only
  the 24 ordinary letters for acrostic positions; ignore punctuation and spaces.
  Editorially supplied/damaged text is flagged, but may enter acrostic matching.

These are searches of the encoded text, not a critical edition. Greek or Latin
OCR intrusions, undeclared line damage, unusual metrical lineation, and encoded
prose-as-verse can remain. No automatic metre recognition or speculative repair
is hidden in the scripts. Source text and flags remain inspectable.

## Dictionary and score

The dictionary comes from tokens in every usable parsed line. Split at
non-Greek characters, preserving elisions as written; do not lemmatize, translate,
consult an external dictionary, or add handpicked target words. The retained
filters are **4–12 normalized letters and at least 2 corpus occurrences**.
`dictionary` stores all forms with an `included` flag. Edition count is provenance,
not a score factor. Duplicate editions can increase both token and letter counts.

For position `k`, let `p_k(c)` be the number of eligible lines whose kth Greek
letter is `c`, divided by the total eligible lines for that position. A short
or unusable line is outside this denominator. Forward and reverse searches share
these positional marginals because reversing a window does not change the
product of its letter probabilities.

The chosen score is exactly:

```
score(s) = dictionary_indicator(s) / product(p_k(c) for c in s)
log2_score(s) = -sum(log2(p_k(c)) for c in s)  # emitted dictionary matches only
```

Non-dictionary strings have score zero and are not emitted. Sort `log2_score`
descending, then word, edition id and start sequence for deterministic ties.
The log value preserves the reciprocal-score ordering and avoids overflow.
There are **no** context, boundary, word-frequency or author factors. This model
assumes independent letters. It strongly favors longer strings and rarer letters;
it is not a probability of intention, a significance test or a correction for
searching many words. `1/product(p)` can be recovered as `2**log2_score`.

## Whole-poem isopsephy

Only explicit TEI `div`/`lg` types **`epigram` or `poem`** are treated as poem
boundaries; these types occur in the downloaded sources. A book, quotation or
arbitrary four-line window is never relabeled as a poem. Consequently poems
encoded only as chapters, whole works, hymns or anonymous verse blocks are
outside this search. This limitation is preferable to inventing boundaries.

With `--group-size 2`, an entire even-length poem of at least four lines must
have all successive two-line sums equal. These are line-pair groups; metre is
not independently established. With `--group-size 1`, every line of an entire
poem of at least two lines must have the same value. Any positive group size is
allowed, with at least two complete groups. Only the entire poem is tested;
partial windows are not searched. A poem with unsupported characters, explicit gaps, damage,
supplied/unclear lines, split lines, nested poems, prose paragraphs or numbering
discontinuities is skipped and recorded in `isopsephy_audit`.

Use traditional Greek letter values, including stigma/digamma=6, koppa=90,
sampi=900. Numeric letter signs contribute their letter values; punctuation,
elision marks and numeral marks contribute zero. No thousands/multiplier syntax,
elision expansion or restoration is performed. Evaluate **both** subscript-iota
conventions; ordinary iota counts in both. Store every line sum and group sum.

AP 8.39 is found by this search, not inserted into its results. The independent
fixture verifies pair totals **6,903 / 6,903** when the iota in `νηῷ` is omitted,
and **6,903 / 6,913** when counted. Numerical equality alone establishes no
intentionality, novelty, chronology or statistical significance.

## Validation

`REPORT.md` records the results, exclusions and verification environment.
The fixture suite runs without downloading corpora:

```sh
python3 -m unittest discover -s tests -v
```

After a full run, verify every candidate's reading path, score and dictionary
membership, check positional frequency counts, and test four documented corpus
examples and AP 8.39:

```sh
python3 tests/verify_corpus.py --database output/new-run.sqlite3 \
  --output output/new-verification.json
```

This also checks SQLite integrity and foreign keys. Assertions must be enabled
(do not run verification scripts with Python's `-O` option).
The fixture tests cover normalization, TEI choices and boundaries, positional
matching, whole-poem arithmetic, and read-only viewer behavior.

## Local viewer

```sh
# From the repository directory:
python3 viewer.py
# Open http://127.0.0.1:8766 on this computer; Ctrl-C stops the server.
```

The viewer reads `output/results.sqlite3` in SQLite read-only mode. It binds
only to 127.0.0.1, has no remote assets or dependencies, and does not edit results.
Search by Greek word, author, title or citation; filter position/direction, sort,
then select a row to read the original passage and marked normalized letters.
The Isopsephy tab shows complete poem passages and both iota conventions.

To browse a fresh scan, export its results and provenance into a new directory:

```sh
python3 tests/save_snapshot.py --database output/new-run.sqlite3 \
  --output-dir output/new-snapshot
python3 tests/compare_snapshot.py --expected output/results.sqlite3 \
  --actual output/new-snapshot/results.sqlite3
python3 viewer.py --database output/new-snapshot/results.sqlite3
```

The exporter requires a full processing database and refuses an existing output
directory. It creates `results.sqlite3`, `schema.sql`, and `provenance/` manifests
using that database's recorded source pins. It does not require corpus checkouts.
The comparison checks every table's rows, including scores, passages, frequencies,
source hashes and audits. The recorded Python version may differ and is reported
separately; no scientific fields are excluded. SQLite file bytes can differ
between SQLite versions even when rows agree. The viewer uses the exported
snapshot without recomputing searches.

The optional browser smoke check uses Node.js 20+ and Playwright solely for testing;
neither is needed to run the scanner or viewer. The tested Playwright version
is pinned in `package-lock.json`. Install it and its matching Chromium once:

```sh
npm ci
npx playwright install chromium
node --check viewer/app.js
# Keep python3 viewer.py running in another terminal, then:
node tests/headless_viewer.cjs
```

The smoke check covers desktop (1365 px) and mobile (390 px), searches,
filters, pagination, forward/reverse highlights, both AP 8.39 totals, and
JavaScript errors. It writes screenshots and a report to `output/new-headless/`.
Set `VIEWER_URL` for a different loopback port or `HEADLESS_OUTPUT` for a different
output directory. `output/headless/` contains the recorded reference check.
