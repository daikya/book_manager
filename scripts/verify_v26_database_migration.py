"""Verify the real v2.6 (schema 7) database migration on a disposable copy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connect(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def snapshot(path, projection=None):
    connection = connect(path)
    try:
        if connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Database integrity check failed')
        if connection.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign key check failed')
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        tables = {}
        names = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for name in (projection if projection is not None else names):
            columns = (projection[name]['columns'] if projection is not None else
                       [row[1] for row in connection.execute(f'PRAGMA table_info({quote(name)})')])
            rows = connection.execute('SELECT ' + ','.join(map(quote, columns)) + ' FROM ' + quote(name)).fetchall()
            content = '\n'.join(sorted(repr(row) for row in rows)).encode('utf-8')
            tables[name] = {'columns': columns, 'count': len(rows),
                            'sha256': hashlib.sha256(content).hexdigest()}
        return {'schema_version': version, 'tables': tables}
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'verify'), required=True)
    parser.add_argument('--source-db', type=Path)
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    work = args.work_dir.resolve()
    baseline_path = work / 'migration_baseline.json'
    target = work / 'data' / 'books.db'
    if args.mode == 'prepare':
        if args.source_db is None:
            parser.error('--source-db is required for prepare')
        source = args.source_db.resolve(strict=True)
        if source == target or source.is_relative_to(work):
            raise ValueError('The source must be outside the new work directory')
        # Require all applications closed so source and its hash remain stable.
        wal = Path(str(source) + '-wal')
        if wal.exists() and wal.stat().st_size:
            raise ValueError('Source WAL is not empty. Close all Book Manager instances first.')
        original_hash = digest(source)
        before = snapshot(source)
        if before['schema_version'] != 7:
            raise ValueError(f"Expected schema 7 (v2.6), got {before['schema_version']}. Do not modify this database.")
        work.mkdir(parents=True, exist_ok=False)
        target.parent.mkdir()
        src = connect(source)
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        if snapshot(target) != before or digest(source) != original_hash:
            raise ValueError('Source changed or copy did not match')
        # Copy only cover cache for visual verification, never the real DB itself.
        covers = source.parent.parent / 'cache' / 'covers'
        if source.parent.name == 'data' and covers.is_dir():
            shutil.copytree(covers, work / 'cache' / 'covers')
        baseline = {'source_path': str(source), 'source_sha256': original_hash, 'before': before}
        baseline_path.write_text(json.dumps(baseline, indent=2), encoding='utf-8')
        print('READY: isolated schema 7 DB copied. Launch EXE with BOOK_MANAGER_HOME set to:')
        print(work)
        print('Source unchanged: True')
        print('Counts:', {name: item['count'] for name, item in before['tables'].items()})
        return
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    before = baseline['before']
    after = snapshot(target, before['tables'])
    failures = []
    if after['schema_version'] != 8:
        failures.append('Target schema is not 8')
    if after['tables'] != before['tables']:
        failures.append('Existing rows/columns or autoincrement sequences changed')
    source_unchanged = digest(Path(baseline['source_path'])) == baseline['source_sha256']
    if not source_unchanged:
        failures.append('Original DB hash changed')
    connection = connect(target)
    try:
        columns = [row[1] for row in connection.execute('PRAGMA table_info(book_items)')]
        if 'reference_isbn' not in columns:
            failures.append('Missing reference_isbn column')
        elif connection.execute('SELECT COUNT(*) FROM book_items WHERE reference_isbn IS NOT NULL').fetchone()[0]:
            failures.append('New reference_isbn values are not NULL')
    finally:
        connection.close()
    backups = list((target.parent / 'schema_backups').glob('before_v7_to_v8_*.db'))
    if not backups or not any(snapshot(path) == before for path in backups):
        failures.append('Matching migration backup not found')
    report = {'result': 'FAIL' if failures else 'PASS', 'source_unchanged': source_unchanged,
              'before': before, 'after': after, 'migration_backup_count': len(backups), 'failures': failures}
    report_path = work / 'migration_verification_report.json'
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Schema:', before['schema_version'], '->', after['schema_version'])
    print('Counts:', {name: item['count'] for name, item in after['tables'].items()})
    print('Source unchanged:', source_unchanged)
    print('Migration backups:', len(backups))
    print('Result:', report['result'])
    for failure in failures:
        print(failure)
    print('Report:', report_path)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
