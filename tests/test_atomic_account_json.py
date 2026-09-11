"""Compile extracted production code; real native atomic replace, synthetic account data."""
from pathlib import Path
import subprocess
from test_oauth_budget_contract import _extract_function

ROOT=Path(__file__).resolve().parents[1]

def test_native_atomic_value_persistence(tmp_path):
    account=(ROOT/'patches/agt-4.7.0/after/src-tauri/src/modules/account.rs').read_text(encoding='utf-8')
    manager=(ROOT/'patches/agt-4.7.0/after/src-tauri/src/proxy/token_manager.rs').read_text(encoding='utf-8')
    oauth=(ROOT/'tests/fixtures/agt-v470-oauth/oauth.rs').read_text(encoding='utf-8')
    start=manager.index('                        let raw = std::fs::read_to_string(&write_path)')
    end=manager.index('                    })();',start)
    block=manager[start:end].replace('crate::modules::account::atomic_write_account_json','atomic_write_account_json')
    start=oauth.index('pub struct TokenResponse {'); response=oauth[start:oauth.index('\n}',start)+2]
    win=account.index('fn atomic_replace_file'); nonwin=account.index('fn atomic_replace_file',win+1)
    code='''use std::{fs,path::PathBuf,sync::{Arc,Mutex},collections::HashMap};
use serde::{Serialize,Deserialize}; use serde_json::Value; use uuid::Uuid; use once_cell::sync::Lazy;
static ACCOUNT_FILE_LOCKS: Lazy<Mutex<HashMap<String,Arc<Mutex<()>>>>> = Lazy::new(||Mutex::new(HashMap::new()));
'''
    code+=_extract_function(account,'fn get_account_lock')+'\n'
    code+='#[cfg(target_os="windows")]\n'+_extract_function(account[win:],'fn atomic_replace_file')+'\n'
    code+='#[cfg(not(target_os="windows"))]\n'+_extract_function(account[nonwin:],'fn atomic_replace_file')+'\n'
    code+=_extract_function(account,'pub(crate) fn atomic_write_account_json')+'\n'
    code+='#[derive(Serialize,Deserialize)]\n'+response+'\n'
    code+='fn persist(write_path:PathBuf,response:TokenResponse,expiry:i64,persisted_client_key:Option<String>)->Result<(), &\'static str>{\n'+block+'}\n'
    code+='''
#[test] fn preserve_unknown_and_rotate(){
 let dir=tempfile::tempdir().unwrap(); let p=dir.path().join("account.json");
 let original=serde_json::json!({"id":"account","future":{"nested":[1,2]},"token":{"future_token":"keep","access_token":"old","refresh_token":"old-r","expiry_timestamp":1}});
 fs::write(&p,original.to_string()).unwrap();
 let response:TokenResponse=serde_json::from_value(serde_json::json!({"access_token":"new","expires_in":3600,"refresh_token":"rotated","id_token":"new-id"})).unwrap();
 persist(p.clone(),response,100,Some("B".into())).unwrap();
 let result:Value=serde_json::from_slice(&fs::read(&p).unwrap()).unwrap();
 assert_eq!(result["future"],original["future"]);assert_eq!(result["token"]["future_token"],"keep");
 assert_eq!(result["token"]["oauth_client_key"],"B");assert_eq!(result["token"]["refresh_token"],"rotated");assert_eq!(result["token"]["access_token"],"new");assert_eq!(result["token"]["id_token"],"new-id");assert_eq!(result["token"]["expires_in"],3600);assert_eq!(result["token"]["expiry_timestamp"],100);
 assert_eq!(fs::read_dir(dir.path()).unwrap().count(),1);
}
#[cfg(target_os="windows")]
#[test] fn native_replace_failure_keeps_old_bytes(){
 use std::os::windows::fs::OpenOptionsExt;
 let dir=tempfile::tempdir().unwrap();let p=dir.path().join("account.json");fs::write(&p,b"old intact").unwrap();
 let held=fs::OpenOptions::new().read(true).share_mode(1).open(&p).unwrap();
 assert!(atomic_write_account_json(&p,&serde_json::json!({"new":true})).is_err());
 assert_eq!(fs::read(&p).unwrap(),b"old intact");assert_eq!(fs::read_dir(dir.path()).unwrap().count(),1);drop(held);
}
'''
    (tmp_path/'src').mkdir();(tmp_path/'src/lib.rs').write_text(code,encoding='utf-8')
    (tmp_path/'Cargo.toml').write_text('[package]\nname="atomic-value-probe"\nversion="0.1.0"\nedition="2021"\n[dependencies]\nserde={version="1",features=["derive"]}\nserde_json="1"\nuuid={version="1",features=["v4"]}\nonce_cell="1"\ntempfile="3"\n',encoding='utf-8')
    result=subprocess.run(['cargo','test','--manifest-path',str(tmp_path/'Cargo.toml')],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'preserve_unknown_and_rotate ... ok' in result.stdout
