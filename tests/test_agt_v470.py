import hashlib,json,shutil,subprocess,sys,unittest,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]; A=R/'patches/agt-4.7.0'
sys.path.insert(0,str(R/'scripts'))
from patch_core import apply,rollback,digest
class V470(unittest.TestCase):
 def test_exact_source_and_roundtrip(self):
  m=json.loads((A/'manifest.json').read_text())
  b=(A/'baseline/src-tauri/src/proxy/token_manager.rs').read_bytes()
  self.assertEqual(len(b),214058)
  self.assertEqual(digest(b),'40c1e4607027b7da9085e233de28c5a3338ff416736ac31e7d20d8dea393780a')
  with tempfile.TemporaryDirectory(prefix='agt 测试 ') as d:
   t=Path(d)/'source space';shutil.copytree(A/'baseline',t)
   self.assertTrue(apply(t,'agt-4.7.0',True));self.assertEqual((t/'src-tauri/src/proxy/token_manager.rs').read_bytes(),b)
   self.assertTrue(apply(t,'agt-4.7.0'));self.assertTrue(apply(t,'agt-4.7.0'))
   for n,h in m['files'].items():self.assertEqual(digest((t/n).read_bytes()),h['after'])
   self.assertTrue(rollback(t,'4.7.0',True));self.assertTrue(rollback(t,'4.7.0'));self.assertTrue(rollback(t,'4.7.0'))
   self.assertEqual((t/'src-tauri/src/proxy/token_manager.rs').read_bytes(),b)
   (t/'src-tauri/src/proxy/token_manager.rs').write_bytes(b'partial')
   self.assertFalse(apply(t,'agt-4.7.0'));self.assertFalse(rollback(t,'4.7.0'))
 def test_helper_identity_and_semantics(self):
  m=json.loads((A/'manifest.json').read_text())
  self.assertEqual(digest((A/'refresh_budget.rs').read_bytes()),m['files']['src-tauri/src/proxy/refresh_budget.rs']['after'])
  s=(A/'after/src-tauri/src/proxy/token_manager.rs').read_text(encoding='utf-8')
  self.assertIn('if current_fails >= 2',s)
  self.assertIn('self.refresh_proxy_token(&mut token, 90).await',s)
  self.assertIn('self.refresh_proxy_token(&mut token, 300).await',s)
  self.assertIn("break 'preferred_refresh_path",s)
  self.assertIn('if let Some(id) = preferred_refresh_failed { attempted.insert(id); }',s)
  self.assertIn('for attempt in 1..=3',s)
  self.assertIn('entry.refresh_token = token.refresh_token.clone()',s)
if __name__=='__main__':unittest.main()
