
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE editions(id INTEGER PRIMARY KEY, urn TEXT UNIQUE, author TEXT, title TEXT,
                      source_path TEXT, sha256 TEXT);
CREATE TABLE poems(edition_id INTEGER REFERENCES editions, poem INTEGER, citation TEXT,
                   kind TEXT, author TEXT, issue TEXT, PRIMARY KEY(edition_id,poem));
CREATE TABLE lines(edition_id INTEGER REFERENCES editions, sequence INTEGER, unit TEXT,
                   poem INTEGER, citation TEXT, raw_text TEXT, text TEXT, letters TEXT,
                   issue TEXT, damaged INTEGER, PRIMARY KEY(edition_id,sequence));
CREATE INDEX lines_poem ON lines(edition_id,poem);
CREATE TABLE dictionary(word TEXT PRIMARY KEY, frequency INTEGER, edition_count INTEGER,
                        included INTEGER);
CREATE TABLE ingest_log(source_path TEXT, status TEXT, detail TEXT);
CREATE TABLE frequencies(position INTEGER, letter TEXT, count INTEGER, total INTEGER,
                         probability REAL, PRIMARY KEY(position,letter));
CREATE TABLE frequency_runs(position INTEGER PRIMARY KEY, eligible_lines INTEGER,
                            short_lines INTEGER, invalid_lines INTEGER);
CREATE TABLE acrostics(direction TEXT, position INTEGER, edition_id INTEGER REFERENCES editions,
                       start_sequence INTEGER, end_sequence INTEGER, word TEXT,
                       log2_score REAL, PRIMARY KEY(direction,position,edition_id,start_sequence,end_sequence,word));
CREATE TABLE isopsephy(edition_id INTEGER, poem INTEGER, group_size INTEGER,
                      convention TEXT, omit_totals TEXT, count_totals TEXT,
                      omit_lines TEXT, count_lines TEXT,
                      PRIMARY KEY(edition_id,poem,group_size));
CREATE TABLE isopsephy_audit(group_size INTEGER, edition_id INTEGER, poem INTEGER, status TEXT,
                            PRIMARY KEY(group_size,edition_id,poem));
CREATE VIEW acrostic_results AS
SELECT a.*,e.urn,e.author,e.title,s.citation AS start_citation,t.citation AS end_citation,
       e.source_path,d.frequency AS word_frequency,d.edition_count
FROM acrostics a JOIN editions e ON e.id=a.edition_id
JOIN lines s ON s.edition_id=a.edition_id AND s.sequence=a.start_sequence
JOIN lines t ON t.edition_id=a.edition_id AND t.sequence=a.end_sequence
JOIN dictionary d ON d.word=a.word;
CREATE VIEW isopsephy_results AS
SELECT i.*,e.urn,e.title,p.author,p.citation,p.kind,e.source_path
FROM isopsephy i JOIN editions e ON e.id=i.edition_id
JOIN poems p ON p.edition_id=i.edition_id AND p.poem=i.poem;
