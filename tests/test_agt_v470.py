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
  self.assertIn('load_account_at_path(&write_path)',s)
  self.assertIn('save_account_at_path(&write_path, &account)',s)
  refresh=s[s.index('async fn refresh_proxy_token'):s.index('async fn get_token_filtered')]
  self.assertNotIn('std::fs::write(&write_path',refresh)
  self.assertIn('lock_account_file_updates()',refresh)
  self.assertIn('account.token.id_token = Some(it.clone())',s)
  self.assertIn('account.token.refresh_token = rt.clone()',s)
  self.assertIn('save_account_at_path',s)
  self.assertIn('typed `Account`', (R/'docs/agt-v470.md').read_text(encoding='utf-8'))
  self.assertIn('不宣称全局并发串行化', (R/'docs/agt-v470.md').read_text(encoding='utf-8'))
 def test_persistence_compile_probe_uses_official_token_model(self):
  official=(R/'tests/fixtures/agt-v470-oauth/token.rs').read_bytes()
  meta=json.loads((R/'tests/fixtures/agt-v470-oauth/source.json').read_text())
  self.assertEqual(digest(official),meta['token_model_lf_sha256'])
  source=(A/'after/src-tauri/src/proxy/token_manager.rs').read_text(encoding='utf-8')
  start=source.index('                        account.token.access_token = response.access_token.clone();')
  end=source.index('                        crate::modules::account::save_account_at_path', start)
  assignments=source[start:end]
  oauth=(R/'tests/fixtures/agt-v470-oauth/oauth.rs').read_text(encoding='utf-8')
  start=oauth.index('pub struct TokenResponse {')
  response=oauth[start:oauth.index('\n}',start)+2]
  with tempfile.TemporaryDirectory(prefix='agt-v470-compile-') as d:
   p=Path(d); (p/'src').mkdir()
   (p/'Cargo.toml').write_text('[package]\nname="agt-v470-persistence-probe"\nversion="0.1.0"\nedition="2021"\n[dependencies]\nserde={version="1",features=["derive"]}\nchrono={version="0.4",features=["clock"]}\n', encoding='utf-8')
   (p/'src/token.rs').write_bytes(official)
   (p/'src/lib.rs').write_text('use serde::{Serialize,Deserialize}; mod token; struct Account { token: token::TokenData }\n#[derive(Serialize,Deserialize)]\n'+response+'\nfn persistence(mut account: Account, response: TokenResponse, expiry:i64) {\n'+assignments+'\n}\n', encoding='utf-8')
   run=subprocess.run(['cargo','check'],cwd=p,capture_output=True,text=True,timeout=120)
   self.assertEqual(run.returncode,0,run.stdout+'\n'+run.stderr)