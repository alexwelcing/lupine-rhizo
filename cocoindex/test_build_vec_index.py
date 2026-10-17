"""In-memory FTS5 and optional real sqlite-vec rollback regressions; no production DB."""
import contextlib
import io
import os
import sqlite3
import unittest
from build_vec_index import build_fts, source_fingerprint


class FtsFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE evidence_chunks(text TEXT, embedding BLOB)")
        self.db.execute("INSERT INTO evidence_chunks VALUES ('oldtoken', X'01')")

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build_fts(self.db, self.db.execute("SELECT count(*) FROM evidence_chunks").fetchone()[0])

    def hits(self, token):
        return self.db.execute("SELECT rowid FROM evidence_chunks_fts WHERE evidence_chunks_fts MATCH ?", (token,)).fetchall()

    def test_same_count_edit_replaces_actual_postings(self):
        self.build()
        self.db.execute("UPDATE evidence_chunks SET text='newtoken'")
        # External-content count matches even while postings are stale.
        self.assertEqual(self.db.execute("SELECT count(*) FROM evidence_chunks_fts").fetchone()[0], 1)
        self.assertEqual(self.hits('newtoken'), [])
        self.build()
        self.assertEqual(self.hits('oldtoken'), [])
        self.assertEqual(self.hits('newtoken'), [(1,)])

    def test_same_count_delete_insert_updates_row_identity(self):
        self.build()
        self.db.execute("DELETE FROM evidence_chunks")
        self.db.execute("INSERT INTO evidence_chunks(rowid,text,embedding) VALUES (9,'replacement',X'02')")
        self.build()
        self.assertEqual(self.hits('oldtoken'), [])
        self.assertEqual(self.hits('replacement'), [(9,)])

    def test_legacy_unstamped_sidecar_is_rebuilt(self):
        self.db.execute("CREATE VIRTUAL TABLE evidence_chunks_fts USING fts5(text, content='evidence_chunks', content_rowid='rowid')")
        self.build()
        self.assertEqual(self.hits('oldtoken'), [(1,)])

    def test_unchanged_source_skips_but_dropped_sidecar_rebuilds(self):
        self.build()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            build_fts(self.db, 1)
        self.assertIn('unchanged', output.getvalue())
        self.db.execute('DROP TABLE evidence_chunks_fts')
        self.build()
        self.assertEqual(self.hits('oldtoken'), [(1,)])

    def test_vector_fingerprint_changes_with_embedding_not_text(self):
        before = source_fingerprint(self.db, 'embedding')
        self.db.execute("UPDATE evidence_chunks SET text='other'")
        self.assertEqual(before, source_fingerprint(self.db, 'embedding'))
        self.db.execute("UPDATE evidence_chunks SET embedding=X'02'")
        self.assertNotEqual(before, source_fingerprint(self.db, 'embedding'))


class InjectedFailureConnection(sqlite3.Connection):
    fail_fts_rebuild = False

    def execute(self, sql, parameters=()):
        if self.fail_fts_rebuild and "VALUES('rebuild')" in sql:
            raise sqlite3.OperationalError('injected FTS rebuild failure')
        return super().execute(sql, parameters)


class AtomicFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:', factory=InjectedFailureConnection)
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE evidence_chunks(text TEXT, embedding BLOB)')
        self.db.execute("INSERT INTO evidence_chunks VALUES ('original', X'01')")
        self.db.commit()

    def test_failed_rebuild_rolls_back_ddl_postings_and_freshness(self):
        build_fts(self.db, 1)
        old = self.db.execute('SELECT * FROM lupine_sidecar_freshness').fetchall()
        self.db.execute("UPDATE evidence_chunks SET text='changed'")
        self.db.commit()
        self.db.fail_fts_rebuild = True
        with self.assertRaisesRegex(sqlite3.OperationalError, 'injected'):
            build_fts(self.db, 1)
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.db.execute('SELECT * FROM lupine_sidecar_freshness').fetchall(), old)
        self.assertEqual(self.db.execute("SELECT rowid FROM evidence_chunks_fts WHERE evidence_chunks_fts MATCH 'original'").fetchall(), [(1,)])
        self.db.fail_fts_rebuild = False
        build_fts(self.db, 1)
        self.assertEqual(self.db.execute("SELECT rowid FROM evidence_chunks_fts WHERE evidence_chunks_fts MATCH 'changed'").fetchall(), [(1,)])

    def test_expected_configuration_is_part_of_freshness(self):
        from build_vec_index import sidecar_current, fts_ddl, vector_ddl
        build_fts(self.db, 1)
        fp = source_fingerprint(self.db, 'text')
        self.assertTrue(sidecar_current(self.db, 'evidence_chunks_fts', fp, fts_ddl()))
        self.assertFalse(sidecar_current(self.db, 'evidence_chunks_fts', fp, 'different schema'))
        self.assertNotEqual(vector_ddl(2), vector_ddl(3))

    def test_failure_preserves_callers_transaction(self):
        build_fts(self.db, 1)
        self.db.execute("UPDATE evidence_chunks SET text='pending'")
        self.db.fail_fts_rebuild = True
        with self.assertRaises(sqlite3.OperationalError):
            build_fts(self.db, 1)
        self.assertTrue(self.db.in_transaction)
        self.assertEqual(self.db.execute('SELECT text FROM evidence_chunks').fetchone()[0], 'pending')
        self.db.rollback()
        self.assertEqual(self.db.execute('SELECT text FROM evidence_chunks').fetchone()[0], 'original')


try:
    import sqlite_vec
except ImportError as error:
    if os.environ.get("REQUIRE_SQLITE_VEC") == "1":
        raise RuntimeError("CI requires sqlite-vec: real vector rollback tests must not skip") from error
    sqlite_vec = None


@unittest.skipIf(sqlite_vec is None, 'sqlite-vec unavailable; no installation performed')
class RealVectorAtomicityTests(unittest.TestCase):
    def test_fts_failure_rolls_back_vector_generation_and_dimension_change(self):
        import struct
        from build_vec_index import build_sidecars
        db = sqlite3.connect(':memory:', factory=InjectedFailureConnection)
        self.addCleanup(db.close)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        db.execute('CREATE TABLE evidence_chunks(text TEXT, embedding BLOB, embedding_space_id TEXT)')
        from embedding_contract import embedding_space
        space = embedding_space('fixture-model', 2, revision='a' * 64)
        original = struct.pack('ff', 1, 0)
        db.execute('INSERT INTO evidence_chunks VALUES (?,?,?)', ('original', original, space))
        db.commit()
        build_sidecars(db, embed_dim=2)
        stamps = db.execute('SELECT * FROM lupine_sidecar_freshness ORDER BY sidecar').fetchall()
        db.execute('UPDATE evidence_chunks SET text=?,embedding=?', ('changed', struct.pack('ff', 0, 1)))
        db.commit()
        db.fail_fts_rebuild = True
        with self.assertRaises(sqlite3.OperationalError):
            build_sidecars(db, embed_dim=2)
        self.assertEqual(bytes(db.execute('SELECT embedding FROM evidence_chunks_vec_row').fetchone()[0]), original)
        self.assertEqual(db.execute('SELECT * FROM lupine_sidecar_freshness ORDER BY sidecar').fetchall(), stamps)
        db.fail_fts_rebuild = False
        # A new dimension must rebuild; incompatible source bytes then fail,
        # preserving the old usable dimension and generation.
        with self.assertRaises(ValueError):
            build_sidecars(db, embed_dim=3)
        self.assertEqual(bytes(db.execute('SELECT embedding FROM evidence_chunks_vec_row').fetchone()[0]), original)


if __name__ == '__main__':
    unittest.main()
