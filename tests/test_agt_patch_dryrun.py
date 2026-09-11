import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from patch_core import apply, digest

class RealPatchTests(unittest.TestCase):
    def check_group(self, group):
        assets=ROOT/'patches'/group
        manifest=json.loads((assets/'manifest.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'source'; shutil.copytree(assets/'baseline',target)
            before={n:(target/n).read_bytes() for n,h in manifest['files'].items() if h['before']}
            self.assertTrue(apply(target,group,True))
            self.assertEqual(before,{n:(target/n).read_bytes() for n in before})
            self.assertTrue(apply(target,group))
            self.assertTrue(apply(target,group))
            for n,h in manifest['files'].items(): self.assertEqual(digest((target/n).read_bytes()),h['after'])
            subprocess.run(['git','init','-q',str(target)],check=True)
            subprocess.run(['git','apply','--reverse','--check',str(assets/manifest['patch'])],cwd=target,check=True)
            if group=='hermes': self.check_real_hermes(target)
            first=next(iter(manifest['files'])); (target/first).write_bytes(b'unknown partial edit')
            snap={n:(target/n).read_bytes() for n in manifest['files']}
            self.assertFalse(apply(target,group))
            self.assertEqual(snap,{n:(target/n).read_bytes() for n in snap})
    def test_agt_real_baseline(self): self.check_group('agt-4.6.7')
    def test_hermes_real_baseline(self): self.check_group('hermes')
    def check_real_hermes(self,target):
        # Execute actual function AST from the applied upstream file, not a mirrored implementation.
        tree=ast.parse((target/'agent/retry_utils.py').read_text(encoding='utf-8'))
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_upstream_wait_seconds')
        ns={'Any':object,'Optional':__import__('typing').Optional,'_error_text':str}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'patched-parser','exec'),ns)
        parser=ns[node.name]
        self.assertEqual(parser('All accounts limited. Wait 12s.'),12)
        self.assertIsNone(parser('503 Token acquisition timeout (5s)'))
        tree=ast.parse((target/'agent/turn_recovery.py').read_text(encoding='utf-8'))
        block=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and 'parse_upstream_wait_seconds' in ast.unparse(n) and isinstance(n.test,ast.Compare) and ast.unparse(n.test)=='_retry_after is None')
        ns.update({'_retry_after':None,'api_error':'All accounts limited. Wait 12s.'})
        exec(compile(ast.Module(body=[block],type_ignores=[]),'patched-wait','exec'),ns)
        self.assertEqual(ns['_retry_after'],13)
        # The Rust harness must import precisely the helper installed by the patch.
    def test_helper_identity(self):
        assets=ROOT/'patches/agt-4.6.7'
        m=json.loads((assets/'manifest.json').read_text())
        self.assertEqual(digest((assets/'refresh_budget.rs').read_bytes()),m['files']['src-tauri/src/proxy/refresh_budget.rs']['after'])

if __name__=='__main__': unittest.main()
