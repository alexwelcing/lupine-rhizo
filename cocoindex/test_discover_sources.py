import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import discover_sources as d

class DiscoveryTests(unittest.TestCase):
    def test_paths_hash_and_privacy(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            (root/'ok.py').write_text('x=1\n')
            (root/'secret.json').write_text('fixture')
            (root/'dist').mkdir();(root/'dist'/'ok.py').write_text('generated')
            (root/'link.py').symlink_to(root/'ok.py')
            (root/'linked').symlink_to(root,target_is_directory=True)
            (root/'binary.txt').write_bytes(b'\xff')
            with (root/'large.py').open('wb') as large:
                large.truncate(d.MAX_FILE+1)  # Sparse oversized fixture; no multi-MiB allocation.
            self.assertEqual(d.source_record(root,'ok.py'),{'path':'ok.py','bytes':4,'sha256':hashlib.sha256(b'x=1\n').hexdigest()})
            for p in ['../ok.py','/etc/passwd','secret.json','dist/ok.py','link.py','linked/ok.py','binary.txt','large.py','.ssh/key.py']:
                self.assertIsNone(d.source_record(root,p),p)
        for root in [Path.home(),Path('/'),Path('/usr'),Path('/System')]:
            with self.assertRaises((ValueError,FileNotFoundError)):d.project_root(root)

    def test_find_only_envelope_and_close_on_failure(self):
        class Fake:
            peak=42
            def __init__(self,binary,root):self.calls=[];self.closed=False;Fake.instance=self
            def rpc(self,method,params):
                self.calls.append((method,params))
                return {} if method=='initialize' else {'content':[{'type':'text','text':'1/84 matches\nok.py\ncursor: 1'}]}
            def send(self,value):pass
            def check(self):pass
            def close(self):self.closed=True
        with tempfile.TemporaryDirectory() as folder,patch.object(d,'Session',Fake):
            Path(folder,'ok.py').write_text('test')
            out=d.discover(folder,'ok',binary='fff')
            self.assertEqual(out['coverage'],'partial');self.assertEqual(out['visibility'],'private')
            self.assertEqual(out['evidenceStatus'],'discovery_only_not_evidence_or_support')
            self.assertEqual(Fake.instance.calls[-1][1]['name'],'find_files');self.assertTrue(Fake.instance.closed)
            with patch.object(Fake,'rpc',side_effect=RuntimeError('protocol')):
                with self.assertRaises(RuntimeError):d.discover(folder,'ok',binary='fff')
                self.assertTrue(Fake.instance.closed)

    def test_protocol_count_and_guards(self):
        for text in ['private text','2/84 matches\none.py','1/84 matches\na.py\nb.py']:
            with self.assertRaises(ValueError):d.parse_paths({'content':[{'type':'text','text':text}]},20)
        with self.assertRaises(RuntimeError):d.parse_paths({'isError':True},20)
        session=object.__new__(d.Session)
        import time
        session.deadline=time.monotonic()+10;session.rss_limit=768*1024;session.peak=0
        session.proc=type('Process',(),{'pid':123})()
        for code,rss in [(1,''),(0,str(769*1024))]:
            with patch.object(d.subprocess,'run',return_value=type('P',(),{'returncode':code,'stdout':rss})()):
                with self.assertRaises(RuntimeError):session.check()
        session.deadline=0
        with self.assertRaises(TimeoutError):session.check()

    def test_jsonl_transport(self):
        import subprocess,sys,selectors,time
        session=object.__new__(d.Session)
        session.deadline=time.monotonic()+3;session.rss_limit=768*1024;session.peak=0;session.sequence=0;session.buffer=b''
        code="import sys,json\nfor line in sys.stdin:\n r=json.loads(line)\n if 'id' in r: print(json.dumps({'id':r['id'],'result':{'echo':r['method']}}),flush=True)"
        session.proc=subprocess.Popen([sys.executable,'-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        session.selector=selectors.DefaultSelector();session.selector.register(session.proc.stdout,selectors.EVENT_READ)
        try:
            with patch.object(d.subprocess,'run',return_value=type('P',(),{'returncode':0,'stdout':'1024'})()):
                self.assertEqual(session.rpc('initialize',{}),{'echo':'initialize'})
        finally:session.close()
        self.assertIsNotNone(session.proc.poll())

if __name__=='__main__':unittest.main()
