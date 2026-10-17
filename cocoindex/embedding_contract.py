"""Stdlib-only embedding identity and retrieval gates; no model/network loading."""
import hashlib
import json
from pathlib import Path

SPLITTER_VERSION = "recursive-1000-overlap200-v1"
TOKENIZER_VERSION = "fts5-default-v1"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def local_model_digest(model):
    """Only local model bytes establish a revision; a mutable remote name does not."""
    root = Path(model)
    if not root.is_dir() or root.is_symlink():
        return None
    digest = hashlib.sha256()
    files = sorted(p for p in root.rglob('*') if p.is_file())
    if not files:
        return None
    for path in files:
        if path.is_symlink():
            return None  # external mutable targets require separate admission
        name = path.relative_to(root).as_posix().encode()
        digest.update(len(name).to_bytes(8, 'big')); digest.update(name)
        with path.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
    return digest.hexdigest()


def embedding_space(model, dimension, backend='sentence_transformers', revision=None):
    return json.dumps({'version': 1, 'model': str(model), 'revision': revision,
        'dimension': dimension, 'backend': backend, 'normalization': 'unit_l2',
        'query_prefix': QUERY_PREFIX if 'bge' in str(model).lower() else '',
        'splitter': SPLITTER_VERSION}, sort_keys=True, separators=(',', ':'))


def safe_semantic_space(space):
    try:
        value = json.loads(space)
        return (value.get('version') == 1 and value.get('backend') == 'sentence_transformers'
                and isinstance(value.get('revision'), str) and len(value['revision']) == 64
                and all(c in '0123456789abcdef' for c in value['revision'])
                and value.get('normalization') == 'unit_l2'
                and type(value.get('dimension')) is int and value['dimension'] > 0)
    except (TypeError, ValueError):
        return False


def common_space(conn):
    columns = {row[1] for row in conn.execute('PRAGMA table_info(evidence_chunks)')}
    if 'embedding_space_id' not in columns:
        return None
    values = conn.execute('SELECT DISTINCT embedding_space_id FROM evidence_chunks LIMIT 2').fetchall()
    if len(values) != 1 or not safe_semantic_space(values[0][0]):
        return None
    return values[0][0]


def semantic_compatible(conn, expected):
    return safe_semantic_space(expected) and common_space(conn) == expected
