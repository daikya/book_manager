"""Verify schema 8 -> 9 on an isolated copy of a Version 2.7 database."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

AUTHOR_TABLES = ('authors', 'author_aliases', 'book_item_authors')


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def connect_readonly(path):
    return sqlite3.connect(Path(path).resolve(strict=True).as_uri() + '?mode=ro', uri=True)


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def snapshot(path, projection=None):
    with closing(connect_readonly(path)) as conn:
        conn.execute('BEGIN')
        if conn.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Database integrity check failed')
        if conn.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign key check failed')
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        names = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        tables = {}
        for name in projection if projection is not None else names:
            if name not in names:
                raise ValueError('Missing original table: ' + name)
            columns = [row[1] for row in conn.execute(f'PRAGMA table_info({quote(name)})')]
            if projection is not None and columns != projection[name]['columns']:
                raise ValueError('Original columns changed: ' + name)
            rows = conn.execute('SELECT ' + ','.join(map(quote, columns)) + ' FROM ' + quote(name)).fetchall()
            content = '\n'.join(sorted(repr(row) for row in rows)).encode('utf-8')
            tables[name] = {'columns': columns, 'count': len(rows),
                            'sha256': hashlib.sha256(content).hexdigest()}
        return {'schema_version': version, 'tables': tables}


def prepare(source_db, work_dir):
    source = Path(source_db).resolve(strict=True)
    work = Path(work_dir).resolve()
    if source == work or source.is_relative_to(work):
        raise ValueError('Source DB must be outside the new work directory')
    if work.exists():
        raise ValueError('Work directory already exists. Choose a new directory; nothing was overwritten.')
    wal = Path(str(source) + '-wal')
    if wal.exists() and wal.stat().st_size:
        raise ValueError('Source WAL is not empty. Close all Book Manager instances first.')
    original_hash = digest(source)
    before = snapshot(source)
    if before['schema_version'] != 8:
        raise ValueError(f"Expected schema 8 (v2.7), got {before['schema_version']}. "
                         'Use an actual schema 8 DB or before_v8_to_v9 backup. Do not downgrade the DB.')
    if any(name in before['tables'] for name in AUTHOR_TABLES):
        raise ValueError('Source already contains author-management tables')
    if 'book_items' not in before['tables']:
        raise ValueError('Not a Book Manager database: missing book_items')
    work.mkdir(parents=True, exist_ok=False)
    target = work / 'data' / 'books.db'
    target.parent.mkdir()
    with closing(connect_readonly(source)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
    if snapshot(target) != before or digest(source) != original_hash:
        raise ValueError('Copy mismatch or source DB changed during preparation')
    covers = source.parent.parent / 'cache' / 'covers'
    if source.parent.name == 'data' and covers.is_dir():
        shutil.copytree(covers, work / 'cache' / 'covers')
    baseline = {'source_path': str(source), 'source_sha256': original_hash, 'before': before}
    (work / 'author_migration_baseline.json').write_text(json.dumps(baseline, indent=2), encoding='utf-8')
    return baseline


def verify(work_dir):
    work = Path(work_dir).resolve(strict=True)
    baseline = json.loads((work / 'author_migration_baseline.json').read_text(encoding='utf-8'))
    before = baseline['before']
    target = work / 'data' / 'books.db'
    failures = []
    after = None
    author_counts = {}
    try:
        after = snapshot(target, before['tables'])
        if after['schema_version'] != 9:
            failures.append('Target schema is not 9')
        if after['tables'] != before['tables']:
            failures.append('Original data or autoincrement sequences changed')
        with closing(connect_readonly(target)) as conn:
            for name in AUTHOR_TABLES:
                author_counts[name] = conn.execute(f'SELECT COUNT(*) FROM {quote(name)}').fetchone()[0]
                if author_counts[name] != 0:
                    failures.append('Expected an empty new table: ' + name)
    except (OSError, sqlite3.Error, ValueError) as error:
        failures.append('Target check failed: ' + str(error))
    source_unchanged = False
    try:
        original = Path(baseline['source_path'])
        source_wal = Path(str(original) + '-wal')
        source_unchanged = (digest(original) == baseline['source_sha256']
                            and not (source_wal.exists() and source_wal.stat().st_size))
        if not source_unchanged:
            failures.append('Original DB hash changed or source has a nonempty WAL')
    except OSError as error:
        failures.append('Original DB could not be checked: ' + str(error))
    backups = list((target.parent / 'schema_backups').glob('before_v8_to_v9_*.db'))
    matching = []
    for backup in backups:
        try:
            if snapshot(backup) == before:
                matching.append(str(backup))
        except (OSError, sqlite3.Error, ValueError):
            continue
    if not matching:
        failures.append('Matching schema 8 migration backup not found')
    report = {'result': 'FAIL' if failures else 'PASS', 'source_unchanged': source_unchanged,
              'before': before, 'after': after, 'author_counts': author_counts,
              'migration_backup_count': len(backups), 'matching_backups': matching,
              'failures': failures}
    report_path = work / 'author_migration_verification_report.json'
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'verify'), required=True)
    parser.add_argument('--source-db', type=Path)
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'prepare':
        if args.source_db is None:
            parser.error('--source-db is required for prepare')
        baseline = prepare(args.source_db, args.work_dir)
        print('READY: isolated schema 8 DB copied. Launch EXE with BOOK_MANAGER_HOME set to:')
        print(args.work_dir.resolve())
        print('Source unchanged: True')
        print('Counts:', {name: value['count'] for name, value in baseline['before']['tables'].items()})
        print('First launch: inspect existing data only; do not register/update/delete books or authors yet.')
        return
    report = verify(args.work_dir)
    print('Schema: 8 ->', report['after']['schema_version'] if report['after'] else 'unavailable')
    print('Counts:', {name: value['count'] for name, value in (report['after'] or {}).get('tables', {}).items()})
    print('New author tables:', report['author_counts'])
    print('Source unchanged:', report['source_unchanged'])
    print('Migration backups:', report['migration_backup_count'])
    print('Result:', report['result'])
    for failure in report['failures']:
        print(failure)
    print('Report:', args.work_dir.resolve() / 'author_migration_verification_report.json')
    if report['failures']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
