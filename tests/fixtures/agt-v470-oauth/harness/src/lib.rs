// Synthetic HTTP/config/logger boundary only. OAuth control flow is included verbatim.
use tokio::time::{sleep, Duration, Instant};
use std::cell::RefCell;
mod reqwest {
 #[derive(Clone,Copy,PartialEq)] pub struct StatusCode(u16);
 impl StatusCode { pub const BAD_REQUEST:Self=Self(400); pub const UNAUTHORIZED:Self=Self(401); pub const FORBIDDEN:Self=Self(403); }
}
mod modules { pub mod logger { pub fn log_warn(_: &str) {} pub fn log_info(_: &str) {} } }
#[derive(Debug)] pub struct TokenResponse;
struct OAuthClientConfig { key: String }
fn get_candidate_clients(_:Option<&str>)->Vec<OAuthClientConfig> { vec![OAuthClientConfig{key:"a".into()},OAuthClientConfig{key:"b".into()}] }
thread_local! { static SCRIPT: RefCell<std::collections::VecDeque<(u64, u8)>> = RefCell::new(Default::default()); static SENT:RefCell<usize>=RefCell::new(0); }
async fn refresh_access_token_once(_: &str,_:Option<&str>,_:&OAuthClientConfig)->Result<TokenResponse,(Option<reqwest::StatusCode>,String)> {
 SENT.with(|s| *s.borrow_mut()+=1);
 let (ms, code)=SCRIPT.with(|s|s.borrow_mut().pop_front().expect("unexpected HTTP request"));
 sleep(Duration::from_millis(ms)).await;
 match code { 0=>Ok(TokenResponse),1=>Err((Some(reqwest::StatusCode::BAD_REQUEST),"invalid_client".into())),_=>Err((Some(reqwest::StatusCode::BAD_REQUEST),"invalid_grant".into())) }
}
include!("official_flow.rs");
#[path="../../../../../patches/agt-4.7.0/refresh_budget.rs"] mod budget;
fn setup(s:Vec<(u64,u8)>) { SCRIPT.with(|v|*v.borrow_mut()=s.into());SENT.with(|v|*v.borrow_mut()=0); }
fn sent()->usize { SENT.with(|s|*s.borrow()) }
async fn run()->Result<TokenResponse,String> { budget::with_refresh_lock(&tokio::sync::Mutex::new(()),refresh_access_token_with_client("synthetic",None,None)).await }
#[tokio::test(start_paused=true)] async fn fast_fallback_succeeds(){ setup(vec![(1000,1),(1000,0)]);assert!(run().await.is_ok()); assert_eq!(sent(),2); }
#[tokio::test(start_paused=true)] async fn slow_fallback_cut_at_15(){ setup(vec![(8000,1),(8000,0)]);let t=Instant::now();assert!(run().await.unwrap_err().contains("15s"));assert_eq!(t.elapsed(),Duration::from_secs(15));assert_eq!(sent(),2); }
#[tokio::test(start_paused=true)] async fn second_confirmation_cut_at_15(){ setup(vec![(14000,2),(2000,0)]);let t=Instant::now();assert!(run().await.unwrap_err().contains("15s"));assert_eq!(t.elapsed(),Duration::from_secs(15));assert_eq!(sent(),2); }
#[tokio::test(start_paused=true)] async fn cancelled_work_sends_no_followup(){ setup(vec![(16000,1),(1000,0)]);assert!(run().await.is_err());sleep(Duration::from_secs(30)).await;assert_eq!(sent(),1); }
#[tokio::test(start_paused=true)] async fn acquisition_caps_at_40(){setup(vec![(16000,1),(16000,1),(16000,1)]);let t=Instant::now();let result=tokio::time::timeout(budget::ACQUISITION_TIMEOUT,async{for _ in 0..3 {let _=run().await;}}).await;assert!(result.is_err());assert_eq!(t.elapsed(),Duration::from_secs(40));assert_eq!(sent(),3);}
