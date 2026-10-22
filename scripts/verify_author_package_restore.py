"""Compare an EXE-exported/restored complete package using read-only DB snapshots."""
from __future__ import annotations
import argparse
from contextlib import closing
import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import zipfile

TABLES = ('book_items', 'tags', 'book_item_tags', 'reading_histories',
          'authors', 'author_aliases', 'book_item_authors')
FILES = {'manifest.csv', 'book_items.csv', 'tags.csv', 'book_item_tags.csv',
         'reading_histories.csv', 'authors.csv', 'author_aliases.csv', 'book_item_authors.csv'}


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def no_wal(path):
    wal=Path(str(path)+'-wal')
    return not (wal.exists() and wal.stat().st_size)


def snapshot(path):
    path=Path(path).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute('BEGIN')
        if conn.execute('PRAGMA user_version').fetchone()[0]!=9:
            raise ValueError('Expected schema 9')
        if conn.execute('PRAGMA integrity_check').fetchall()[0][0]!='ok':
            raise ValueError('Integrity check failed')
        if conn.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign key check failed')
        rows={table:conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in TABLES}
        # Export/import reassigns numeric IDs. Map by original entity order.
        maps={table:{row['id']:index for index,row in enumerate(sorted(rows[table],key=lambda row:row['id']),1)}
              for table in ('book_items','tags','authors')}
        groups={}
        references={'book_item_id':'book_items','tag_id':'tags','author_id':'authors'}
        for table in TABLES:
            columns=sorted(row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')
                           if row[1] not in ('id','cover_image_path'))
            normalized=[]
            for row in rows[table]:
                values=[]
                if table in maps:values.append(maps[table][row['id']])
                for column in columns:
                    value=row[column]
                    values.append(maps[references[column]][value] if column in references else value)
                normalized.append(tuple(values))
            data='\n'.join(sorted(repr(row) for row in normalized)).encode('utf-8')
            groups[table]={'columns':columns,'count':len(normalized),'sha256':hashlib.sha256(data).hexdigest()}
        return groups


def prepare(source_home,work_dir):
    source=(Path(source_home)/'data'/'books.db').resolve(strict=True)
    work=Path(work_dir).resolve()
    if work.exists() or source.is_relative_to(work):
        raise ValueError('Choose a new work directory outside the source home')
    if not no_wal(source):raise ValueError('Close all Book Manager instances first (source WAL is not empty)')
    original_hash=digest(source)
    groups=snapshot(source)
    if any(groups[table]['count']==0 for table in ('authors','author_aliases','book_item_authors')):
        raise ValueError('Add at least one author, alias and book-author relation in the EXE test DB before this check')
    if digest(source)!=original_hash:raise ValueError('Source DB changed during snapshot')
    work.mkdir(parents=True,exist_ok=False)
    target=work/'restore_home'/'data'/'books.db'
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    from book_manager.database.initializer import initialize_database
    initialize_database(target)
    baseline={'source_db':str(source),'source_sha256':original_hash,'groups':groups}
    (work/'author_package_baseline.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
    return baseline


def verify(work_dir, *, compare_current=False):
    work=Path(work_dir).resolve(strict=True)
    baseline=json.loads((work/'author_package_baseline.json').read_text(encoding='utf-8'))
    source=Path(baseline['source_db'])
    initial_baseline_hash=baseline['source_sha256']
    if compare_current:
        if not no_wal(source):raise ValueError('Close all Book Manager instances before comparing current data')
        before_hash=digest(source)
        baseline={**baseline,'source_sha256':before_hash,'groups':snapshot(source)}
    failures=[]
    after={}
    try:
        unchanged=digest(source)==baseline['source_sha256'] and no_wal(source)
    except OSError:
        unchanged=False
    if not unchanged:failures.append('Source DB changed or could not be checked')
    try:
        after=snapshot(work/'restore_home'/'data'/'books.db')
        for table in TABLES:
            if after[table]!=baseline['groups'][table]:failures.append('Restored data mismatch: '+table)
    except (OSError,ValueError,KeyError,sqlite3.Error) as error:
        failures.append('Restored DB check failed: '+str(error))
    package=work/'author_full_data.zip'
    package_hash=None
    try:
        with zipfile.ZipFile(package) as archive:
            names=archive.namelist()
            if set(names)!=FILES or len(names)!=len(FILES):raise ValueError('Expected exactly 8 package CSV files')
            manifest=dict(list(csv.reader(io.StringIO(archive.read('manifest.csv').decode('utf-8-sig'))))[1:])
            if manifest.get('format_version')!='3':raise ValueError('Expected package format 3')
        package_hash=digest(package)
    except (OSError,ValueError,UnicodeError,zipfile.BadZipFile,KeyError) as error:
        failures.append('Package check failed: '+str(error))
    try:
        unchanged_at_end=digest(source)==baseline['source_sha256'] and no_wal(source)
        original_unchanged=digest(source)==initial_baseline_hash and no_wal(source)
    except OSError:
        unchanged_at_end=False
        original_unchanged=False
    if not unchanged_at_end and unchanged:
        failures.append('Source DB changed during comparison')
    unchanged=unchanged and unchanged_at_end
    report={'result':'FAIL' if failures else 'PASS','source_unchanged':unchanged,
            'comparison_basis':'current_source' if compare_current else 'prepare_baseline',
            'original_baseline_source_unchanged':original_unchanged,
            'expected':baseline['groups'],'restored':after,'package_sha256':package_hash,'failures':failures,
            'excluded_fields':['numeric database IDs','sqlite_sequence','book_items.cover_image_path']}
    report_name='author_package_current_verification_report.json' if compare_current else 'author_package_verification_report.json'
    (work/report_name).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('prepare','verify','compare-current'),required=True)
    parser.add_argument('--source-home',type=Path)
    parser.add_argument('--work-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.mode=='prepare':
        if args.source_home is None:parser.error('--source-home is required for prepare')
        baseline=prepare(args.source_home,args.work_dir)
        print('READY. Counts:',{name:group['count'] for name,group in baseline['groups'].items()})
        print('Export ZIP to:',args.work_dir.resolve()/'author_full_data.zip')
        print('Restore BOOK_MANAGER_HOME:',args.work_dir.resolve()/'restore_home')
    else:
        report=verify(args.work_dir,compare_current=args.mode=='compare-current')
        print('Comparison basis:',report['comparison_basis'])
        print('Source unchanged during comparison:',report['source_unchanged'])
        print('Source matches original baseline:',report['original_baseline_source_unchanged'])
        print('Restored counts:',{name:group['count'] for name,group in report['restored'].items()})
        print('Result:',report['result'])
        for failure in report['failures']:print(failure)
        name='author_package_current_verification_report.json' if args.mode=='compare-current' else 'author_package_verification_report.json'
        print('Report:',args.work_dir.resolve()/name)
        if report['failures']:raise SystemExit(1)


if __name__=='__main__':main()
