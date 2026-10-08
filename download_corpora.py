#!/usr/bin/env python3
"""Download exactly the two repository revisions recorded by the old Python run."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
PINS = [
    ('canonical-greekLit', 'https://github.com/PerseusDL/canonical-greekLit.git',
     '790c84289edbdbe289dd7b752bfea29f0af4299d'),
    ('First1KGreek', 'https://github.com/OpenGreekAndLatin/First1KGreek.git',
     '4c9c843d80ee94b4371f52add5f7d68bbfe7ba4c'),
]


def git(folder, *args):
    return subprocess.check_output(['git', '-C', str(folder), *args], text=True).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination', type=Path, default=ROOT / 'corpora')
    a = p.parse_args()
    a.destination.mkdir(parents=True, exist_ok=True)
    records = []
    for name, url, commit in PINS:
        folder = a.destination / name
        if folder.exists():
            # An existing directory is only reused if already exact and clean.
            if git(folder, 'rev-parse', 'HEAD') != commit or git(folder, 'status', '--porcelain'):
                raise SystemExit(f'Refusing to alter existing checkout: {folder}')
        else:
            folder.mkdir()
            git(folder, 'init', '-q')
            git(folder, 'fetch', '--depth=1', url, commit)
            git(folder, 'checkout', '--detach', 'FETCH_HEAD')
        records.append({'directory': name, 'url': url, 'commit': commit})
        print(f'{name}: {commit}')
    manifest = a.destination / 'repositories.json'
    content = json.dumps(records, indent=2) + '\n'
    if manifest.exists() and manifest.read_text() != content:
        raise SystemExit(f'Refusing to replace different provenance: {manifest}')
    manifest.write_text(content)


if __name__ == '__main__':
    main()
