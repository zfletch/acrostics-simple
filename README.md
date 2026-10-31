# Greek acrostics, simply

Six small Python command-line scripts, one shared text helper, SQLite output,
and no Python dependencies. Requires Python 3.9+ and Git. Everything runs locally.
The existing research bundle and Claude project are not inputs that these scripts modify.

## License

The project's original source code is licensed under the [MIT License](LICENSE),
copyright (c) 2026 Zachary Fletcher.

The MIT License does not relicense third-party material, downloaded corpora, or
source texts and excerpts included in provenance files or generated results.
Those materials retain their upstream licenses and attribution requirements.
See [source attribution](provenance/source-attribution.json), the preserved
[Perseus license](provenance/canonical-greekLit-license.md) and
[First1KGreek license](provenance/First1KGreek-license.md) (CC BY-SA 4.0), and
individual TEI headers for applicable source terms.

## Browse the results online

The public viewer is at **https://zfletch.github.io/acrostics-simple/**. The source
repository stays private. The site publishes the existing 27,470 acrostic
candidates, 20 whole-poem isopsephy results, their required Greek passages, and
edition attribution. Its [methods and licenses](https://zfletch.github.io/acrostics-simple/methods.html)
explain the scores, iota conventions, source pins, and text normalization.

The website runs entirely in the browser. It does not need the Mini or a Python
server. Passage files load by edition only when a result is selected. The local
viewer below remains available independently.

## Browse the included results locally

Clone the private repository using an account with access:

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

## Build or update the public viewer

`build_pages.py` reads the committed snapshot in SQLite read-only mode and writes
a **new** output directory. It refuses an existing destination. It neither runs
the research pipeline nor exports the SQLite file, corpus repositories, private
logs, or uploaded PDFs. Only the static viewer, result index, required passage
files, attribution, and license notices enter the publication artifact.

```sh
python3 -m unittest discover -s tests -v
python3 build_pages.py --output _site
python3 -m http.server 8877 --bind 127.0.0.1 --directory _site
# Open http://127.0.0.1:8877/; Ctrl-C stops this separate preview.
```

The query-parity test uses Node.js to compare the browser data layer with
`viewer.py`; all exported rows and passage lines are also checked against SQLite.
`tests/headless_pages.cjs` adds browser checks with an existing Playwright install
(`PLAYWRIGHT_PATH` can name its module directory). Set `PAGES_URL` to the preview
or live site URL, including its trailing slash. Its default URL is
`http://127.0.0.1:8877/acrostics-simple/`; use a parent preview directory to test
that project path. Browser screenshots and results go to ignored
`output/pages-browser/` or `HEADLESS_OUTPUT`.

The **Publish results viewer** Actions workflow builds from `main`, runs the
Python and Node parity checks, uploads only `_site/`, and deploys to the
`github-pages` environment. Relevant changes to `main` trigger publication; the
workflow can also be dispatched manually. Updating the bundled snapshot publishes
its findings, so review the intended public content before pushing such changes.
The public manifest records the exact source commit and snapshot SHA-256.

To roll back, revert the unwanted publication commit on `main` and deploy again.
For this initial Pages addition the pre-publication reference is
`7b91542cd1747ab2d633542d8015eb828c4d3270`. Disabling Pages withdraws the site
without changing repository visibility or research files. The separate
`publication-cleanup` branch is not part of this deployment.

## Reproduce a scan

Run these commands from the repository directory (on the original Mini,
`~/a/acrostics-simple`). Downloading the pinned source repositories requires
network access; subsequent processing runs locally.

```sh
python3 download_corpora.py
python3 build_dictionary.py --database output/new-run.sqlite3
python3 calculate_frequencies.py --database output/new-run.sqlite3 --position 1
python3 calculate_frequencies.py --database output/new-run.sqlite3 --position 2
python3 search_forward.py --database output/new-run.sqlite3 --position 1
python3 search_reverse.py --database output/new-run.sqlite3 --position 1
python3 search_forward.py --database output/new-run.sqlite3 --position 2
python3 search_reverse.py --database output/new-run.sqlite3 --position 2
python3 search_isopsephy.py --database output/new-run.sqlite3 --group-size 2
python3 search_isopsephy.py --database output/new-run.sqlite3 --group-size 1
python3 -m unittest discover -s tests -v
```

The original full processing run is `output/research.sqlite3` on the Mini; it
is excluded from Git. A fresh clone includes `output/results.sqlite3`, the
compact results snapshot, and the commands above create a separate full run at
`output/new-run.sqlite3`. The builder refuses an existing output filename;
use a fresh filename for each rebuild. The other five processing commands only
accept this project's full processing database format. Searches replace only
results for their own direction/position or group size. Recalculating a frequency
position removes that position's old acrostic scores; rerun both searches afterwards.
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
snapshot, provenance, comparison results, and validation evidence are tracked.

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

These are the revisions recorded in the original Python database's `metadata`
and original `fetch_corpora.sh`, not the newer Claude corpus snapshot:

| Repository | Commit |
|---|---|
| https://github.com/PerseusDL/canonical-greekLit | `790c84289edbdbe289dd7b752bfea29f0af4299d` |
| https://github.com/OpenGreekAndLatin/First1KGreek | `4c9c843d80ee94b4371f52add5f7d68bbfe7ba4c` |

Scope is **all available encoded Greek verse lines in those snapshots**, including
verse quoted in prose, alternate editions, and repository subdirectories. It is
not all surviving Greek literature, and it is not the prose token population.
Files use the original filename rule (`-grc` or `.grc`, `.xml`). Perseus is read
first, then First1K, sorted within each; a repeated edition URN is kept once.
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
  patterns spanning them; the scope is deliberately narrower than the old scan.
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
The historical heuristic is documented separately in `provenance/inspection-notes.txt`.

## Isopsephy really searches poems

Only explicit TEI `div`/`lg` types **`epigram` or `poem`** are treated as poem
boundaries; these types occur in the downloaded sources. A book, quotation or
arbitrary four-line window is never relabeled as a poem. Consequently poems
encoded only as chapters, whole works, hymns or anonymous verse blocks are
outside this search. This limitation is preferable to inventing boundaries.

With `--group-size 2`, an entire even-length poem of at least four lines must
have all successive two-line sums equal. These are line-pair groups; metre is
not independently established. With `--group-size 1`, every line of an entire
poem of at least two lines must have the same value. Any positive group size is
allowed, with at least two complete groups; no sliding-window search or halves
category is added. A poem with unsupported characters, explicit gaps, damage,
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

## Validation and previous results

See `REPORT.md`, `output/tests.txt`, `output/comparison.json` and the full
`output/candidate-differences.json`. To repeat the read-only historical comparison:

```sh
python3 tests/compare_legacy.py \
  --legacy ~/a/acrostics/regenerated/reconciled.sqlite3 \
  --database output/research.sqlite3 --output output
```

The historical comparison also needs the separate original research database;
it is optional and is not required for a fresh scan or the viewer. The recorded
comparison evidence is included in this repository.

Three archived candidate sets are reproduced exactly with their historical
rules. Reverse position 2 has a rule replay but no archived table. The current
parser deliberately changes boundaries and readings; do not expect identical
candidate counts, vocabulary or scores. Every removed candidate is classified.
The original research, databases, paper and Claude source were left untouched.

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

The optional `tests/save_snapshot.py` exporter reads specifically from
`output/research.sqlite3`. To use it in a fresh clone, choose that full-database
filename for every processing command above instead of `output/new-run.sqlite3`.
Archive the included compact snapshot before running the exporter; it refuses
to replace an existing `output/results.sqlite3`. The exporter also regenerates
`output/schema.sql` and two provenance manifests. Preserve any previous full run
before choosing the same filename. This is a static result snapshot: the viewer
does not silently recompute the corpus or run searches on the server.

The UI is a separate second Git commit. A third follow-up commit fixes a
malformed Forward menu option and widens mobile controls, after headless testing.
Both earlier commits are preserved. All 17 core/viewer tests pass, as do the
JavaScript syntax check and the optional headless browser checks.

The computer-use in-app browser was unavailable; its browser inventory was empty,
and native app discovery reported the Mac locked. After an explicit request for
headless checks, the existing Playwright installation and cached Chromium were
used in a fresh headless context with `chromiumSandbox:true`, without accessing
the desktop session. Desktop (1365 px) and mobile (390 px) screenshots were
captured and inspected. Search, direction/position filters, paging, score order,
forward/reverse highlights and AP8.39 totals pass, with no horizontal overflow
or JavaScript errors. See `output/headless/`.

The optional browser check requires a separately installed Playwright package
and cached browser; neither is a dependency of the six scripts or viewer:

```sh
# Keep the local viewer running first. Use an existing Playwright installation.
PLAYWRIGHT_PATH=/absolute/path/to/playwright-core node tests/headless_viewer.cjs
```
