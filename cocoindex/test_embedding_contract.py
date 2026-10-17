"""Stdlib-only identity/fallback tests; never import a model or production DB."""
import ast
import contextlib
import io
import sqlite3
import types
import unittest
from pathlib import Path
from embedding_contract import embedding_space, semantic_compatible, common_space
from build_vec_index import build_sidecars, source_fingerprint


class EmbeddingContractTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.space = embedding_space('fixture', 2, revision='a' * 64)

    def test_legacy_unknown_mixed_and_hash_vectors_are_not_semantic(self):
        self.db.execute('CREATE TABLE evidence_chunks(text TEXT, embedding BLOB)')
        self.db.execute("INSERT INTO evidence_chunks VALUES ('lexical',X'01')")
        self.assertFalse(semantic_compatible(self.db,self.space))
        self.db.execute('ALTER TABLE evidence_chunks ADD COLUMN embedding_space_id TEXT')
        self.assertFalse(semantic_compatible(self.db,self.space))
        self.db.execute('UPDATE evidence_chunks SET embedding_space_id=?',(self.space,))
        self.assertTrue(semantic_compatible(self.db,self.space))
        self.db.execute("INSERT INTO evidence_chunks VALUES ('other',X'01',?)",(embedding_space('other',2,revision='b'*64),))
        self.assertIsNone(common_space(self.db))
        self.db.execute('DELETE FROM evidence_chunks WHERE text=?',('other',))
        self.db.execute('UPDATE evidence_chunks SET embedding_space_id=?',(embedding_space('hash',2,backend='hash_test',revision='sha256-v1'),))
        self.assertFalse(semantic_compatible(self.db,self.space))

    def test_revision_and_normalization_are_generation_identity(self):
        self.db.execute('CREATE TABLE evidence_chunks(text TEXT, embedding BLOB, embedding_space_id TEXT)')
        self.db.execute("INSERT INTO evidence_chunks VALUES ('text',X'01',?)",(self.space,))
        before=source_fingerprint(self.db,'embedding')
        other=embedding_space('fixture',2,revision='b'*64)
        self.db.execute('UPDATE evidence_chunks SET embedding_space_id=?',(other,))
        self.assertNotEqual(before,source_fingerprint(self.db,'embedding'))
        self.assertFalse(semantic_compatible(self.db,self.space))
        self.assertFalse(semantic_compatible(self.db,embedding_space('fixture',2)))

    def test_legacy_build_is_lexical_only_preserves_source(self):
        self.db.execute('CREATE TABLE evidence_chunks(text TEXT, embedding BLOB)')
        self.db.execute("INSERT INTO evidence_chunks VALUES ('knownterm',X'01')")
        with contextlib.redirect_stdout(io.StringIO()):build_sidecars(self.db)
        self.assertEqual(self.db.execute("SELECT rowid FROM evidence_chunks_fts WHERE evidence_chunks_fts MATCH 'knownterm'").fetchall(),[(1,)])
        self.assertEqual(self.db.execute('SELECT text,embedding FROM evidence_chunks').fetchall(),[('knownterm',b'\x01')])
        self.assertIsNone(self.db.execute("SELECT 1 FROM sqlite_master WHERE name='evidence_chunks_vec_row'").fetchone())

    def test_actual_query_function_uses_lexical_without_embedding_unknown_rows(self):
        # Compile only the real function with explicit capability stubs; no heavy imports.
        tree=ast.parse(Path(__file__).with_name('query.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='semantic_search')
        def forbidden(*args):raise AssertionError('Unknown vectors reached embedder/extension')
        env={'sqlite3':sqlite3,'sys':types.SimpleNamespace(stderr=io.StringIO()),
             'pipeline':types.SimpleNamespace(EMBED_SPACE_ID=self.space),
             'semantic_compatible':semantic_compatible,'keyword_search':lambda *args:['lexical-result'],
             '_load_vec':forbidden,'_safe_embed':forbidden}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'actual-semantic-search','exec'),env)
        self.db.execute('CREATE TABLE evidence_chunks(text TEXT, embedding BLOB)')
        self.assertEqual(env['semantic_search'](self.db,'query',3,None),['lexical-result'])


    def test_real_query_embedding_failure_uses_lexical_not_hash_vector(self):
        tree=ast.parse(Path(__file__).with_name('query.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='semantic_search')
        def unavailable(*args):raise RuntimeError('model unavailable')
        def forbidden(*args):raise AssertionError('Hash/vector query must not run')
        env={'sqlite3':sqlite3,'sys':types.SimpleNamespace(stderr=io.StringIO()),
             'pipeline':types.SimpleNamespace(EMBED_SPACE_ID=self.space),
             'semantic_compatible':lambda *args:True,'keyword_search':lambda *args:['lexical-result'],
             '_load_vec':lambda *args:True,'_table_exists':lambda *args:True,
             '_safe_embed':unavailable,'_try_vec0_query':forbidden,
             'np':types.SimpleNamespace(asarray=lambda value,**kwargs:value,float32='fixture')}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'actual-semantic-search','exec'),env)
        self.assertEqual(env['semantic_search'](self.db,'query',3,None),['lexical-result'])


    def test_actual_keyword_search_falls_back_on_same_count_text_edit(self):
        from build_vec_index import build_fts, sidecar_matches_source
        tree=ast.parse(Path(__file__).with_name('query.py').read_text())
        names={'keyword_search','_table_exists','_like_search','_bm25_search','_row'}
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        env={'sqlite3':sqlite3,'sidecar_matches_source':sidecar_matches_source}
        exec(compile(ast.Module(body=functions,type_ignores=[]),'actual-keyword-search','exec'),env)
        self.db.execute('CREATE TABLE evidence_chunks(id TEXT,source_file TEXT,kind TEXT,ref_id TEXT,text TEXT,chunk_start INT,chunk_end INT)')
        self.db.execute("INSERT INTO evidence_chunks VALUES ('one','fixture','claim','one','oldtoken',0,8)")
        build_fts(self.db,1)
        self.assertEqual(env['keyword_search'](self.db,'oldtoken',3,None)[0]['id'],'one')
        self.db.execute("UPDATE evidence_chunks SET text='newtoken'")
        self.assertEqual(env['keyword_search'](self.db,'oldtoken',3,None),[])
        self.assertEqual(env['keyword_search'](self.db,'newtoken',3,None)[0]['id'],'one')


if __name__=='__main__':unittest.main()
