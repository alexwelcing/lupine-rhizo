#!/usr/bin/env python3
"""Private, bounded fff fuzzy-path discovery. Never evidence or support ingestion."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import time

MAX_FILE = 2 * 1024 * 1024
DENIED_DIRS = {'.git', '.ssh', '.aws', '.codex', '.cache', '.config', '.gnupg',
               'node_modules', 'dist', 'build', 'target', '__pycache__', '.venv',
               'venv', 'outputs', 'exports', 'logs', 'sessions', 'archives', 'credentials'}
EXTENSIONS = {'.py', '.ts', '.tsx', '.js', '.mjs', '.cjs', '.json', '.md', '.sql',
              '.toml', '.yaml', '.yml', '.css', '.html', '.lean', '.txt', '.sh', '.rs', '.go', '.c', '.h'}


def project_root(value):
    raw = Path(value).absolute()
    root = raw.resolve(strict=True)
    home = Path.home().resolve()
    if raw.is_symlink() or not root.is_dir() or root == home or root in home.parents or root in {
        Path('/'), Path('/tmp'), Path('/private'), Path('/private/tmp'), Path('/var'), Path('/private/var'),
        Path('/System'), Path('/Library'), Path('/usr'), Path('/opt'), Path('/Applications')}:
        raise ValueError('An explicit project directory is required; broad/system roots are forbidden')
    if any(root == Path(base) or Path(base) in root.parents for base in ('/System', '/Library', '/usr', '/opt', '/Applications', '/etc', '/private/etc', '/bin', '/sbin', '/dev', '/proc', '/sys')):
        raise ValueError('System trees are forbidden')
    if any(part.lower() in DENIED_DIRS for part in root.parts):
        raise ValueError('Private or generated roots are forbidden')
    return root


def source_record(root, relative):
    """Read only a regular UTF-8 source through no-follow directory descriptors."""
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(p in {'.', '..'} or p.startswith('.') or p.lower() in DENIED_DIRS for p in path.parts):
        return None
    lower = path.name.lower()
    if path.suffix.lower() not in EXTENSIONS or any(word in lower for word in ('secret', 'credential', 'password', 'token', 'private_key')) or lower.endswith('lock.json'):
        return None
    import stat
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(file_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE:
                return None
            chunks = []
            size = 0
            while True:
                chunk = os.read(file_fd, min(65536, MAX_FILE + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_FILE:
                    return None
            body = b''.join(chunks)
            body.decode('utf-8', errors='strict')
            if b'\x00' in body:
                return None
            return {'path': path.as_posix(), 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': size}
        finally:
            os.close(file_fd)
    except (OSError, UnicodeError):
        return None
    finally:
        os.close(fd)


class Session:
    def __init__(self, binary, root, timeout=60, rss_mib=768):
        self.deadline = time.monotonic() + timeout
        self.rss_limit = rss_mib * 1024
        self.peak = 0
        self.sequence = 0
        self.buffer = b''
        self.proc = subprocess.Popen([str(binary), str(root), '--no-update-check', '--no-warmup',
            '--no-content-indexing', '--no-watch', '--max-cached-files', '0', '--log-level', 'off'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=root)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)

    def check(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('fff exceeded 60-second discovery deadline')
        sample = subprocess.run(['ps', '-o', 'rss=', '-p', str(self.proc.pid)], capture_output=True,
                                text=True, timeout=min(2, remaining))
        if sample.returncode or not sample.stdout.strip().isdigit():
            raise RuntimeError('Cannot enforce fff RSS guard')
        rss = int(sample.stdout.strip())
        self.peak = max(self.peak, rss)
        if rss > self.rss_limit:
            raise RuntimeError('fff exceeded RSS guard')

    def send(self, value):
        self.proc.stdin.write((json.dumps(value) + '\n').encode())
        self.proc.stdin.flush()

    def rpc(self, method, params):
        self.sequence += 1
        request_id = self.sequence
        self.check()
        self.send({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params})
        while True:
            self.check()
            if b'\n' not in self.buffer:
                if not self.selector.select(min(.2, max(0, self.deadline-time.monotonic()))):
                    continue
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError('fff ended before response')
                self.buffer += chunk
                if len(self.buffer) > 262144:
                    raise RuntimeError('fff protocol output exceeded limit')
                continue
            line, self.buffer = self.buffer.split(b'\n', 1)
            value = json.loads(line)
            if value.get('id') != request_id:
                continue
            if 'error' in value:
                if method == 'tools/call' and value['error'].get('message') == 'Index is still building; retry shortly':
                    time.sleep(min(.1, max(0, self.deadline-time.monotonic())))
                    self.check()
                    self.sequence += 1
                    request_id = self.sequence
                    self.send({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params})
                    continue
                raise RuntimeError('fff protocol/tool request failed')
            return value['result']

    def close(self):
        self.selector.close()
        self.proc.stdin.close()
        # Terminate promptly even if a server waits indefinitely after stdin EOF.
        if self.proc.poll() is None:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=2)
        self.proc.stdout.close()


def parse_paths(result, limit):
    if result.get('isError'):
        raise RuntimeError('fff rejected discovery')
    content = result.get('content')
    if not isinstance(content, list) or len(content) != 1 or content[0].get('type') != 'text':
        raise ValueError('Unexpected fff discovery response')
    lines = content[0]['text'].strip().splitlines()
    import re
    if not lines or not re.fullmatch(r'\d+/\d+ matches', lines[0]):
        raise ValueError('Unexpected fff path protocol')
    paths = [line for line in lines[1:] if not re.fullmatch(r'cursor: \d+', line)]
    expected = int(lines[0].split('/')[0])
    if len(paths) != expected or len(paths) > limit or len(set(paths)) != len(paths):
        raise ValueError('Unexpected fff result count')
    return paths


def discover(root, query, limit=10, binary=None):
    root = project_root(root)
    if not isinstance(query, str) or not query.strip() or len(query) > 500 or any(ord(c) < 32 for c in query):
        raise ValueError('A bounded nonempty path query is required')
    if not 1 <= limit <= 20:
        raise ValueError('Result limit must be 1..20')
    binary = binary or os.environ.get('FFF_BIN') or shutil.which('fff-mcp')
    if not binary:
        raise ValueError('fff-mcp not found; set FFF_BIN or --binary')
    session = Session(binary, root)
    try:
        session.rpc('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                    'clientInfo': {'name': 'lupine-private-source-discovery', 'version': '1'}})
        session.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        result = session.rpc('tools/call', {'name': 'find_files', 'arguments': {'query': query, 'maxResults': limit}})
        paths = parse_paths(result, limit)
        records = []
        for path in paths:
            session.check()
            record = source_record(root, path)
            if record is not None:
                records.append(record)
        session.check()
        return {'schema': 'lupine.private_source_discovery.v1', 'visibility': 'private',
                'method': 'fff_fuzzy_path', 'query': query, 'projectRoot': str(root),
                'coverage': 'partial', 'records': records, 'returned': len(records),
                'rejected': len(paths)-len(records), 'peakSampledRssKiB': session.peak,
                'evidenceStatus': 'discovery_only_not_evidence_or_support',
                'limitations': ['Fuzzy paths are not exact text matches; ignored, unreturned or filtered files remain unsearched.',
                                'Hashes identify bytes read now; no scientific verification or evidence ingestion occurred.']}
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--query', required=True)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--binary')
    args = parser.parse_args()
    try:
        print(json.dumps(discover(args.root, args.query, args.limit, args.binary)))
    except Exception:
        parser.exit(1, 'Private source discovery failed; no results accepted. Check root, protocol and resource guards.\n')


if __name__ == '__main__':
    main()
