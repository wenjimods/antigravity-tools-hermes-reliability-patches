"""Extract production refresh + upstream client ordering; mock HTTP/config only, not E2E."""
from pathlib import Path
import subprocess
from test_oauth_budget_contract import _extract_function as extract
ROOT=Path(__file__).resolve().parents[1]

def test_executable_client_continuity(tmp_path):
    p=ROOT/'patches/agt-4.7.0'
    manager=(p/'after/src-tauri/src/proxy/token_manager.rs').read_text(encoding='utf-8')
    oauth=(p/'baseline/src-tauri/src/modules/oauth.rs').read_text(encoding='utf-8')
    account=(p/'after/src-tauri/src/modules/account.rs').read_text(encoding='utf-8')
    (tmp_path/'src').mkdir()
    (tmp_path/'src/budget.rs').write_bytes((p/'refresh_budget.rs').read_bytes())
    atomic='use std::{fs,path::PathBuf,sync::{Arc,Mutex},collections::HashMap};use serde_json::Value;use uuid::Uuid;use once_cell::sync::Lazy;\nstatic ACCOUNT_FILE_LOCKS:Lazy<Mutex<HashMap<String,Arc<Mutex<()>>>>>=Lazy::new(||Mutex::new(HashMap::new()));\n'
    atomic+=extract(account,'fn get_account_lock')+'\n'+extract(account,'pub(crate) fn atomic_write_account_json')+'\n'
    a=account.index('fn atomic_replace_file');b=account.index('fn atomic_replace_file',a+1)
    atomic+='#[cfg(target_os="windows")]\n'+extract(account[a:],'fn atomic_replace_file')+'\n#[cfg(not(target_os="windows"))]\n'+extract(account[b:],'fn atomic_replace_file')
    atomic+='\nstatic GLOBAL:Mutex<()>=Mutex::new(());pub fn lock_account_file_updates()->Result<std::sync::MutexGuard<\'static,()>,String>{GLOBAL.lock().map_err(|e|e.to_string())}\n'
    (tmp_path/'src/account.rs').write_text(atomic,encoding='utf-8')
    a=oauth.index('pub struct TokenResponse');response=oauth[a:oauth.index('\n}',a)+2]
    flow='use serde::{Serialize,Deserialize};\n#[derive(Serialize,Deserialize)]\n'+response+'\n'
    flow+='''
mod reqwest {#[derive(Clone,Copy,PartialEq)] pub struct StatusCode(u16);impl StatusCode{pub const BAD_REQUEST:Self=Self(400);pub const UNAUTHORIZED:Self=Self(401);pub const FORBIDDEN:Self=Self(403);}}
#[derive(Clone)] struct OAuthClientConfig{key:String}
struct Registry{clients:Vec<OAuthClientConfig>,active_key:String}
static REG:std::sync::OnceLock<std::sync::RwLock<Registry>>=std::sync::OnceLock::new();
fn oauth_registry()->&'static std::sync::RwLock<Registry>{REG.get_or_init(||std::sync::RwLock::new(Registry{clients:vec![],active_key:String::new()}))}
fn get_client_by_key<'a>(clients:&'a [OAuthClientConfig],key:&str)->Option<&'a OAuthClientConfig>{clients.iter().find(|c|c.key==key)}
pub static SENT:std::sync::Mutex<Vec<String>>=std::sync::Mutex::new(Vec::new());
pub fn setup(enterprise:bool){let mut r=oauth_registry().write().unwrap();r.clients=if enterprise{vec![OAuthClientConfig{key:"antigravity_enterprise".into()}]}else{vec![OAuthClientConfig{key:"A".into()},OAuthClientConfig{key:"B".into()}]};r.active_key=r.clients[0].key.clone();SENT.lock().unwrap().clear();}
async fn refresh_access_token_once(_: &str,_:Option<&str>,client:&OAuthClientConfig)->Result<TokenResponse,(Option<reqwest::StatusCode>,String)>{
 SENT.lock().unwrap().push(client.key.clone());if client.key=="A"{return Err((Some(reqwest::StatusCode::BAD_REQUEST),"invalid_client".into()));}
 Ok(TokenResponse{access_token:"new".into(),expires_in:3600,token_type:"Bearer".into(),refresh_token:Some("rotated".into()),id_token:Some("new-id".into()),oauth_client_key:Some(client.key.clone())})
}
'''
    for sig in ['fn get_candidate_clients','fn is_client_mismatch_error','pub async fn refresh_access_token_with_client']:
        flow+='\n'+extract(oauth,sig)
    (tmp_path/'src/oauth.rs').write_text(flow,encoding='utf-8')
    struct=extract(manager,'pub struct ProxyToken')
    method=extract(manager,'async fn refresh_proxy_token')
    normal=extract(manager,'fn normalize_refreshed_oauth_client_key')
    loader=next(line.strip() for line in manager.splitlines() if 'let oauth_client_key = token_obj.get(' in line)
    code='''pub mod modules {pub mod logger {pub fn log_warn(_: &str){}pub fn log_info(_: &str){}}pub mod oauth {include!("oauth.rs");} pub mod account {include!("account.rs");}}
#[path="budget.rs"] mod refresh_budget;
mod proxy {
use std::{path::PathBuf,sync::Arc,collections::{HashMap,HashSet}};use dashmap::DashMap;
'''
    code+='#[derive(Clone,Default)]\n'+struct+'\n'+normal+'\n'
    code+='struct TokenManager{tokens:DashMap<String,ProxyToken>,refresh_locks:DashMap<String,Arc<tokio::sync::Mutex<()>>>,invalid_grant_failures:DashMap<String,u32>}\nimpl TokenManager{'+method+'}\n'
    code+='fn load_key(value:&serde_json::Value)->Option<String>{let token_obj=value["token"].as_object().unwrap();'+loader+'oauth_client_key}\n'
    code+='''
async fn scenario(enterprise:bool, saved:Option<&str>){
 crate::modules::oauth::setup(enterprise);
 let dir=tempfile::tempdir().unwrap();let path=dir.path().join("id.json");
 let json=serde_json::json!({"id":"id","unknown":{"keep":true},"token":{"expiry_timestamp":0,"refresh_token":"old","unknown_token":7,"oauth_client_key":saved}});
 std::fs::write(&path,json.to_string()).unwrap();
 let mut token=ProxyToken{account_id:"id".into(),account_path:path.clone(),refresh_token:"old".into(),oauth_client_key:load_key(&json),..Default::default()};
 let manager=TokenManager{tokens:DashMap::new(),refresh_locks:DashMap::new(),invalid_grant_failures:DashMap::new()};manager.tokens.insert("id".into(),token.clone());
 manager.refresh_proxy_token(&mut token,90).await.unwrap();
 assert_eq!(token.refresh_token,"rotated");let entry=manager.tokens.get("id").unwrap();assert_eq!(entry.refresh_token,"rotated");assert_eq!(entry.oauth_client_key,token.oauth_client_key);drop(entry);
 let expected=if enterprise{None}else{Some("B".to_string())};assert_eq!(token.oauth_client_key,expected);
 let mut stored=None;for _ in 0..200 {let bytes=std::fs::read(&path).unwrap();let val:serde_json::Value=serde_json::from_slice(&bytes).unwrap();if val["token"]["refresh_token"]=="rotated"{stored=Some(val);break;}tokio::time::sleep(std::time::Duration::from_millis(10)).await;}
 let val=stored.expect("background persistence completed");assert_eq!(val["token"]["oauth_client_key"].as_str(),expected.as_deref());if enterprise{assert!(val["token"].get("oauth_client_key").is_none());}
 assert_eq!(val["unknown"],json["unknown"]);assert_eq!(val["token"]["unknown_token"],7);
 let sent=crate::modules::oauth::SENT.lock().unwrap();if enterprise{assert_eq!(*sent,vec!["antigravity_enterprise"]);}else if saved.is_some(){assert_eq!(*sent,vec!["B"]);}else{assert_eq!(*sent,vec!["A","B"]);}
}
#[tokio::test] async fn preferred_b_before_active_a(){scenario(false,Some("B")).await;}
#[tokio::test] async fn legacy_enterprise_remains_unset(){scenario(true,None).await;}
#[tokio::test] async fn fallback_updates_key(){scenario(false,None).await;}
}
'''
    (tmp_path/'src/lib.rs').write_text(code,encoding='utf-8')
    (tmp_path/'Cargo.toml').write_text('[package]\nname="client-continuity"\nversion="0.1.0"\nedition="2021"\n[dependencies]\ntokio={version="1",features=["macros","rt","sync","time","test-util","net","io-util"]}\nserde={version="1",features=["derive"]}\nserde_json="1"\nuuid={version="1",features=["v4"]}\nonce_cell="1"\nchrono="0.4"\ndashmap="6"\ntracing="0.1"\ntempfile="3"\n',encoding='utf-8')
    result=subprocess.run(['cargo','test','--manifest-path',str(tmp_path/'Cargo.toml'),'--','--test-threads=1'],capture_output=True,text=True,timeout=240)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    for name in ['preferred_b_before_active_a','legacy_enterprise_remains_unset','fallback_updates_key']:
        assert name+' ... ok' in result.stdout
