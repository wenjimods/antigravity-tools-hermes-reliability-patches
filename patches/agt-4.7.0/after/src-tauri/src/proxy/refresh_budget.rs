//! Independent account-refresh limits; the acquisition guard is only a final safety net.
use std::future::Future;
use std::time::Duration;
use tokio::sync::Mutex;

pub const ACQUISITION_TIMEOUT: Duration = Duration::from_secs(40);
pub const REFRESH_TIMEOUT: Duration = Duration::from_secs(15);
pub const LOCK_TIMEOUT: Duration = Duration::from_secs(1);

/// Construct/poll the work only after obtaining the per-account lock. The work
/// must re-read current token state, so concurrent requests do not refresh twice.
pub async fn with_refresh_lock<T, F>(lock: &Mutex<()>, work: F) -> Result<T, String>
where
    F: Future<Output = Result<T, String>>,
{
    let _guard = tokio::time::timeout(LOCK_TIMEOUT, lock.lock())
        .await
        .map_err(|_| "Token refresh lock timeout (1s)".to_string())?;
    tokio::time::timeout(REFRESH_TIMEOUT, work)
        .await
        .map_err(|_| "OAuth refresh timeout (15s)".to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{
        atomic::{AtomicUsize, Ordering},
        Arc,
    };
    #[tokio::test(start_paused = true)]
    async fn refresh_slower_than_old_guard_succeeds() {
        let lock = Mutex::new(());
        assert_eq!(
            with_refresh_lock(&lock, async {
                tokio::time::sleep(Duration::from_secs(6)).await;
                Ok(42)
            })
            .await
            .unwrap(),
            42
        );
    }
    #[tokio::test(start_paused = true)]
    async fn refresh_timeout_releases_lock_and_does_not_report_invalid_grant() {
        let lock = Mutex::new(());
        let error = with_refresh_lock(&lock, std::future::pending::<Result<(), String>>())
            .await
            .unwrap_err();
        assert!(error.contains("OAuth refresh timeout"));
        assert!(!error.contains("invalid_grant"));
        assert!(lock.try_lock().is_ok());
    }
    #[tokio::test(start_paused = true)]
    async fn busy_account_does_not_run_work() {
        let lock = Mutex::new(());
        let _guard = lock.lock().await;
        let ran = AtomicUsize::new(0);
        let result = with_refresh_lock(&lock, async {
            ran.fetch_add(1, Ordering::SeqCst);
            Ok(())
        })
        .await;
        assert!(result.unwrap_err().contains("lock timeout"));
        assert_eq!(ran.load(Ordering::SeqCst), 0);
    }
    #[tokio::test(start_paused = true)]
    async fn timed_out_account_leaves_budget_for_next_account() {
        let lock = Mutex::new(());
        let result = tokio::time::timeout(ACQUISITION_TIMEOUT, async {
            let first =
                with_refresh_lock(&lock, std::future::pending::<Result<u8, String>>()).await;
            assert!(first.is_err());
            with_refresh_lock(&lock, async {
                tokio::time::sleep(Duration::from_secs(6)).await;
                Ok(2)
            })
            .await
        })
        .await
        .unwrap()
        .unwrap();
        assert_eq!(result, 2);
    }
    #[tokio::test(start_paused = true)]
    async fn exhausted_pool_is_bounded() {
        let lock = Mutex::new(());
        let start = tokio::time::Instant::now();
        let result = tokio::time::timeout(ACQUISITION_TIMEOUT, async {
            for _ in 0..10 {
                let _ =
                    with_refresh_lock(&lock, std::future::pending::<Result<(), String>>()).await;
            }
        })
        .await;
        assert!(result.is_err());
        assert_eq!(start.elapsed(), ACQUISITION_TIMEOUT);
        assert!(lock.try_lock().is_ok());
    }
    #[tokio::test(start_paused = true)]
    async fn concurrent_waiter_rechecks_state_under_lock() {
        let lock = Arc::new(Mutex::new(()));
        let refreshed = Arc::new(AtomicUsize::new(0));
        let mut tasks = Vec::new();
        for _ in 0..2 {
            let lock = lock.clone();
            let refreshed = refreshed.clone();
            tasks.push(tokio::spawn(async move {
                with_refresh_lock(&lock, async {
                    if refreshed.load(Ordering::SeqCst) == 0 {
                        tokio::time::sleep(Duration::from_millis(100)).await;
                        refreshed.fetch_add(1, Ordering::SeqCst);
                    }
                    Ok(())
                })
                .await
            }));
        }
        for task in tasks {
            task.await.unwrap().unwrap();
        }
        assert_eq!(refreshed.load(Ordering::SeqCst), 1);
    }
    #[tokio::test]
    async fn real_six_second_io_is_not_aborted_by_old_five_second_limit() {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let server = tokio::spawn(async move {
            let (mut socket, _) = listener.accept().await.unwrap();
            tokio::time::sleep(Duration::from_secs(6)).await;
            socket.write_all(b"mock-refresh-complete").await.unwrap();
        });
        let lock = Mutex::new(());
        let start = std::time::Instant::now();
        let result = with_refresh_lock(&lock, async {
            let mut socket = tokio::net::TcpStream::connect(address).await.map_err(|e|e.to_string())?;
            let mut response = Vec::new();
            socket.read_to_end(&mut response).await.map_err(|e|e.to_string())?;
            Ok(response)
        }).await.unwrap();
        server.await.unwrap();
        assert_eq!(result, b"mock-refresh-complete");
        assert!(start.elapsed() >= Duration::from_secs(6));
    }

    #[tokio::test(start_paused = true)]
    async fn upstream_failure_is_not_a_successful_old_token() {
        let lock = Mutex::new(());
        assert_eq!(
            with_refresh_lock::<(), _>(&lock, async { Err("invalid_grant".into()) })
                .await
                .unwrap_err(),
            "invalid_grant"
        );
    }
}
