"""Disposable offline CocoIndex legacy->new schema smoke, intended for CI.

Requires the existing pipeline dependencies; never installs or loads a model.
Failure is a release gate, not authorization to recreate any production database.
"""
from pathlib import Path
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time


def run():
    here = Path(__file__).resolve().parent
    current = (here / 'main.py').read_text()
    # Reproduce the immediately preceding target schema using the actual engine,
    # not a hand-built SQLite approximation. The embedding fixture is test-only.
    legacy = current.replace('    embedding_space_id: str | None\n', '').replace('            embedding_space_id=space,\n', '')
    if legacy == current:
        raise RuntimeError('Legacy fixture transform no longer matches; review smoke explicitly')
    deadline = time.monotonic() + 60
    with tempfile.TemporaryDirectory(prefix='lupine-cocoindex-schema-') as directory:
        root = Path(directory)
        (root / 'data').mkdir(); (root / 'empty-library').mkdir()
        (root / 'data' / 'fixture.jsonl').write_text(json.dumps({
            'id': 'fictional-schema-smoke', 'kind': 'claim', 'ref_id': 'fictional-schema-smoke',
            'text': 'Fictional engine schema fixture, not scientific evidence.',
        }) + '\n')
        shutil.copyfile(here / 'embedding_contract.py', root / 'embedding_contract.py')
        source = root / 'main.py'; database = root / 'evidence.db'
        env = {**os.environ, 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
               'HF_DATASETS_OFFLINE': '1', 'EVIDENCE_TEST_HASH_ONLY': '1',
               'EVIDENCE_REQUIRE_REAL_EMBEDDINGS': '0', 'EVIDENCE_INDEX_CORPUS': '0',
               'EVIDENCE_LIBRARY_ROOT': str(root / 'empty-library'),
               'EVIDENCE_EMBED_MODEL': 'BAAI/bge-small-en-v1.5',
               'EVIDENCE_DB_PATH': str(database), 'COCOINDEX_DB': str(root / 'engine'),
               'HF_HOME': str(root / 'offline-hf'), 'PYTHONDONTWRITEBYTECODE': '1'}
        # Do not inherit a caller's module override or a production DB location.
        env['PYTHONPATH'] = str(root)

        def update(label):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError('Engine smoke exceeded the 60-second total budget')
            result = subprocess.run([sys.executable, '-B', '-m', 'cocoindex.cli', 'update', str(source)],
                                    cwd=root, env=env, text=True, capture_output=True, timeout=remaining)
            if result.returncode:
                # Fixture-only output, bounded; never include a production payload.
                raise RuntimeError(f'{label} failed: engine schema migration unsupported or dependency/API mismatch. '
                                   f'Preserve production data; no automatic rebuild.\n{result.stderr[-3000:]}')
            if not database.exists():
                raise RuntimeError(f'{label}: engine did not create the configured disposable target')

        def rows():
            with sqlite3.connect(database) as db:
                columns = {row[1] for row in db.execute('PRAGMA table_info(evidence_chunks)')}
                stable = db.execute('SELECT id, text, ref_id, embedding FROM evidence_chunks ORDER BY id').fetchall()
                spaces = db.execute('SELECT embedding_space_id FROM evidence_chunks ORDER BY id').fetchall() if 'embedding_space_id' in columns else None
            return columns, stable, spaces

        source.write_text(legacy); update('Legacy engine fixture')
        old_columns, old_rows, _ = rows()
        if 'embedding_space_id' in old_columns or len(old_rows) != 1:
            raise RuntimeError('Legacy engine fixture did not establish the intended one-row old schema')
        source.write_text(current); update('Legacy-to-current target update')
        columns, new_rows, spaces = rows()
        if 'embedding_space_id' not in columns or new_rows != old_rows or not spaces:
            raise RuntimeError('Nullable schema addition was not lossless. Preserve production data; explicit migration required')
        # Untouched retained rows may remain NULL: never invent a generation for
        # legacy vectors. If the engine reprocesses a row, only hash_test is valid.
        if any(row[0] is not None and json.loads(row[0])['backend'] != 'hash_test' for row in spaces):
            raise RuntimeError('Offline smoke unexpectedly used a real embedding backend')
        update('Repeated current update')
        if rows() != (columns, new_rows, spaces):
            raise RuntimeError('Repeated unchanged update changed fixture rows/schema')
        # A deliberate source edit requires a newly produced row to be tagged.
        (root / 'data' / 'fixture.jsonl').write_text(json.dumps({
            'id': 'fictional-schema-smoke', 'kind': 'claim', 'ref_id': 'fictional-schema-smoke',
            'text': 'Changed fictional engine fixture; still not scientific evidence.',
        }) + '\n')
        update('Changed-source current update')
        _, changed_rows, changed_spaces = rows()
        if len(changed_rows) != 1 or changed_rows[0][1] == old_rows[0][1] or not changed_spaces or any(
                not row[0] or json.loads(row[0])['backend'] != 'hash_test' for row in changed_spaces):
            raise RuntimeError('Newly produced rows did not receive their actual hash-test identity')
        print(json.dumps({'ok': True, 'scope': 'disposable offline engine schema fixture only',
                          'rows': len(new_rows), 'legacy_addition_preserved_rows': True,
                          'repeated_update_stable': True, 'changed_source_tagged': True,
                          'legacy_null_is_unknown': True, 'embedding_backend': 'hash_test',
                          'production_touched': False}))
    # TemporaryDirectory cleans target DB, engine state and fixture caches on all exits.


if __name__ == '__main__':
    try:
        run()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
