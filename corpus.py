"""Shared TEI reading and Greek normalization, so all six scripts use one text."""
import unicodedata as U
import xml.etree.ElementTree as ET

NS = '{http://www.tei-c.org/ns/1.0}'
LANG = '{http://www.w3.org/XML/1998/namespace}lang'
LETTERS = 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'
FOLD = {'ϲ': 'Σ', 'Ϲ': 'Σ', 'Ͻ': 'Σ', 'ϐ': 'Β', 'ϑ': 'Θ',
        'ϰ': 'Κ', 'ϱ': 'Ρ', 'ϕ': 'Φ', 'ϖ': 'Π'}
VALUES = dict(zip('ΑΒΓΔΕϚΖΗΘΙΚΛΜΝΞΟΠϞΡΣΤΥΦΧΨΩϠ',
                  list(range(1, 10)) + list(range(10, 100, 10)) + list(range(100, 1000, 100))))
VALUES.update({'Ϝ': 6, 'Ϙ': 90})
# These are editorial text, not the selected reading of a verse.
DROP = {'note', 'bibl', 'ref', 'head', 'speaker', 'label', 'del', 'stage',
        'docAuthor', 'docTitle', 'fw', 'figure', 'graphic', 'castList'}
POEM_TYPES = {'epigram', 'poem'}  # Types actually present in the pinned corpora.
SPEAKER_ONLY = 'speaker_label_only'
# This edition's CTS declaration names its book/chapter units "epigram".
# Do not infer poem boundaries from chapter length, author, or numerical equality.
CHAPTER_EPIGRAM_EDITION = 'urn:cts:greekLit:tlg7000.tlg001.perseus-grc6'
EPIGRAM_POINTER = "#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n='$1']/tei:div[@n='$2'])"


def normalized(text, count_iota=False, numeric=False):
    """NFD before uppercasing; subscript ignored unless explicitly requested."""
    result = []
    for raw in text:
        decomposed = '\u0345' if raw == '\u1fbe' else U.normalize('NFD', raw)
        for char in decomposed:
            if char == '\u0345':
                if count_iota:
                    result.append('Ι')
            elif char in {'ʼ', 'ʹ', 'ʹ'}:  # Elision / numeral signs, not alphabetic letters.
                continue
            elif U.category(char).startswith('M'):
                continue
            else:
                letter = FOLD.get(char, char.upper())
                if letter in (VALUES if numeric else LETTERS):
                    result.append(letter)
                elif numeric and char.isalpha():
                    raise ValueError(f'Unsupported alphabetic character: {char!r}')
    return ''.join(result)


def tokens(text):
    # Split at non-Greek letters, not accents; retain elided forms as written.
    text = U.normalize('NFD', text.replace('\u1fbe', ''))
    folded = ''.join('' if U.category(c).startswith('M') else
                     (FOLD.get(c, c.upper()) if FOLD.get(c, c.upper()) in LETTERS else ' ')
                     for c in text)
    return folded.split()


def tag(element):
    return element.tag.rsplit('}', 1)[-1]


def reading(element):
    """Choose lem/corr/reg/expan once; never concatenate alternate readings."""
    name = tag(element)
    if name in DROP or (name == 'foreign' and element.get(LANG, 'grc') not in {'grc', 'el'}):
        return ''
    if name in {'app', 'choice'}:
        choices = ('lem',) if name == 'app' else ('corr', 'reg', 'expan')
        for choice in choices:
            selected = next((x for x in element if tag(x) == choice), None)
            if selected is not None:
                return reading(selected)
        raise ValueError(f'Unresolved <{name}> reading')
    # Empty milestones preserve their following tail text.
    return (element.text or '') + ''.join(reading(c) + (c.tail or '') for c in element)


def speaker_label_only(line):
    """Recognize only complete, nonempty speaker labels with no verse text.

    Retain the source row, ordinal and citation; this is not a general rule for
    dropping empty lines, editorial content, fragments, or damaged text.
    """
    return (not line.get('part') and not (line.text or '').strip() and len(line) > 0
            and all(tag(c) == 'label' and c.get('type') == 'speaker' and len(c) == 0
                    and (c.text or '').strip() and not (c.tail or '').strip() for c in line))


def line_boundary(before, after):
    """Explain a discontinuity between adjacent original XML line records."""
    if before['unit'] != after['unit']:
        return 'unit_boundary'
    if after['sequence'] != before['sequence'] + 1:
        return 'xml_line_discontinuity'
    x, y = before['citation'].rsplit('.', 1)[-1], after['citation'].rsplit('.', 1)[-1]
    if x.isdecimal() and y.isdecimal() and int(y) != int(x) + 1:
        return 'line_number_discontinuity'
    return ''


def metrical_lines(rows):
    """Yield (verse row, preceding barrier), crossing only explicit speaker rows.

    Check every original adjacency, including the skipped speaker records.
    A label therefore cannot hide a numbering gap, XML gap, or unit boundary.
    Unusable real verses remain in the stream as barriers.
    """
    previous, barrier = None, ''
    for row in rows:
        if previous is not None:
            barrier = barrier or line_boundary(previous, row)
        previous = row
        if row['issue'] == SPEAKER_ONLY:
            continue
        yield row, barrier
        barrier = ''


def extract(path):
    """Return edition metadata, explicit poems, lines, and parse audit counts.

    Every XML <l> has an ordinal. Rejected lines remain barriers. Every div
    (even an unnumbered one), quote, and poem-labelled lg has a distinct unit.
    This deliberately over-splits some works rather than joining distinct poems.
    """
    root = ET.parse(path).getroot()  # Strict: no silent recovery of broken XML.
    body = root.find('.//' + NS + 'body')
    if body is None:
        return None
    elements = list(body.iter())
    ids = {e: i for i, e in enumerate(elements)}
    parents = {child: parent for parent in elements for child in parent}

    def ancestors(e):
        chain = []
        while e in parents:
            e = parents[e]
            chain.append(e)
        return list(reversed(chain))

    def kind(e):
        return e.get('subtype', e.get('type', '')).strip().lower()

    def is_poem(e):
        if tag(e) in {'div', 'lg'} and kind(e) in POEM_TYPES:
            return True
        parent = parents.get(e)
        return (chapter_epigrams and tag(e) == 'div' and kind(e) == 'chapter'
                and bool(e.get('n')) and parent is not None and tag(parent) == 'div'
                and kind(parent) == 'book' and bool(parent.get('n'))
                and parents.get(parent) is edition)

    def citation(chain):
        return '.'.join(e.get('n') for e in chain
                        if tag(e) == 'div' and kind(e) != 'edition' and e.get('n'))

    editions = [e for e in elements if tag(e) == 'div' and kind(e) == 'edition']
    if len(editions) != 1:
        raise ValueError(f'Expected one edition division, found {len(editions)}')
    edition = editions[0]
    urn = edition.get('n') or path.stem
    chapter_epigrams = (urn == CHAPTER_EPIGRAM_EDITION and any(
        pattern.get('n') == 'epigram' and pattern.get('replacementPattern') == EPIGRAM_POINTER
        for refs in root.findall('.//' + NS + 'refsDecl') if refs.get('n') == 'CTS'
        for pattern in refs.findall(NS + 'cRefPattern')))
    statement = root.find('.//' + NS + 'titleStmt')
    author = statement.find(NS + 'author') if statement is not None else None
    titles = statement.findall(NS + 'title') if statement is not None else []
    title = next((e for e in titles if e.get(LANG) == 'grc'), titles[0] if titles else None)
    metadata = {'urn': urn,
                'author': ' '.join(''.join(author.itertext()).split()) if author is not None else 'Unknown',
                'title': ' '.join(''.join(title.itertext()).split()) if title is not None else path.stem}
    poems = {}
    for e in elements:
        if is_poem(e):
            poet = e.find(NS + 'docAuthor')
            issue = ''
            if any(is_poem(c) for c in e.iter() if c is not e):
                issue = 'nested_poem'
            # A poem containing prose paragraphs is not certified as all-verse.
            if any(tag(c) in {'gap', 'damage'} for c in e.iter()):
                issue = 'gap_or_damage'
            if e.find('.//' + NS + 'p') is not None:
                issue = 'prose_paragraph'
            poems[ids[e]] = (citation(ancestors(e) + [e]), kind(e),
                            ' '.join(''.join(poet.itertext()).split()) if poet is not None else metadata['author'], issue)
    lines = []
    for sequence, line in enumerate(body.iter(NS + 'l')):
        chain = ancestors(line)
        # Editorial quoted lines do not enter either corpus statistics or poems.
        if any(tag(e) in DROP or tag(e) == 'l' for e in chain):
            continue
        if edition not in chain:
            continue
        unit_chain = [e for e in chain if tag(e) in {'div', 'quote', 'cit', 'q'} or is_poem(e)]
        unit = '/'.join(str(ids[e]) for e in unit_chain)
        poem = next((ids[e] for e in reversed(chain) if is_poem(e)), None)
        loc = '.'.join(filter(None, [citation(chain), line.get('n', '?')]))
        issue = ''
        try:
            text = ' '.join(reading(line).split())
        except ValueError as error:
            text, issue = '', str(error)
        if line.get('part', '').upper() in {'I', 'M', 'F'}:
            issue = 'split_line'  # Never treat pieces as complete metrical lines.
        if line.find('.//' + NS + 'l') is not None:
            issue = 'nested_line'
        letters = normalized(text)
        if not letters:
            issue = issue or 'no_greek_letters'
        # A gap may conceal missing letters; retain text but mark uncertainty.
        damage = any(tag(e) in {'gap', 'damage', 'supplied', 'unclear'} for e in line.iter())
        if issue == 'no_greek_letters' and not damage and speaker_label_only(line):
            issue = SPEAKER_ONLY
        raw = ' '.join(''.join(line.itertext()).split())
        lines.append((sequence, unit, poem, loc, raw, text, letters, issue, int(damage)))
    return metadata, poems, lines


def open_database(path):
    """Only open a database created by this project, never an old research DB."""
    import sqlite3
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=rw', uri=True)
    if db.execute('PRAGMA application_id').fetchone()[0] != 1094931027:
        db.close()
        raise ValueError('Not a database created by build_dictionary.py')
    db.row_factory = sqlite3.Row
    return db
