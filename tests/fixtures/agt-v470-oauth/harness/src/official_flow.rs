fn is_client_mismatch_error(status: reqwest::StatusCode, error_text: &str) -> bool {
    let text = error_text.to_ascii_lowercase();
    status == reqwest::StatusCode::BAD_REQUEST
        || status == reqwest::StatusCode::UNAUTHORIZED
        || status == reqwest::StatusCode::FORBIDDEN
        || text.contains("unauthorized_client")
        || text.contains("invalid_client")
}

pub async fn refresh_access_token_with_client(
    refresh_token: &str,
    account_id: Option<&str>,
    preferred_client_key: Option<&str>,
) -> Result<TokenResponse, String> {
    let candidates = get_candidate_clients(preferred_client_key);
    if candidates.is_empty() {
        return Err("No OAuth clients configured".to_string());
    }

    let mut attempt_errors: Vec<String> = Vec::new();

    for (idx, client_cfg) in candidates.iter().enumerate() {
        let mut last_attempt_err = None;
        let mut recovered_token = None;

        // 对同一个 OAuth Client 最多执行 2 次尝试（首次遇 invalid_grant 进行 500ms 短退避重试确认）
        for retry_count in 0..2 {
            if retry_count > 0 {
                tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
            }
            match refresh_access_token_once(refresh_token, account_id, client_cfg).await {
                Ok(token_res) => {
                    recovered_token = Some(token_res);
                    break;
                }
                Err((status_opt, err_msg)) => {
                    let is_grant_error = err_msg.contains("invalid_grant");
                    if is_grant_error && retry_count == 0 {
                        crate::modules::logger::log_warn(&format!(
                            "[OAuth] Client [{}] 收到疑似 invalid_grant，将在 500ms 后进行二次退避确认...",
                            client_cfg.key
                        ));
                        last_attempt_err = Some((status_opt, err_msg));
                        continue;
                    }
                    last_attempt_err = Some((status_opt, err_msg));
                    break;
                }
            }
        }

        if let Some(token_res) = recovered_token {
            if idx > 0 {
                crate::modules::logger::log_info(&format!(
                    "Refresh recovered via fallback OAuth client [{}]",
                    client_cfg.key
                ));
            }
            return Ok(token_res);
        }

        if let Some((status_opt, err_msg)) = last_attempt_err {
            let should_fallback = status_opt
                .map(|status| is_client_mismatch_error(status, &err_msg))
                .unwrap_or(false);

            attempt_errors.push(format!("{} => {}", client_cfg.key, err_msg));

            if should_fallback {
                crate::modules::logger::log_warn(&format!(
                    "Refresh failed for client [{}], trying next client: {}",
                    client_cfg.key, err_msg
                ));
                continue;
            }

            return Err(format!(
                "Refresh failed for client [{}]: {}",
                client_cfg.key, err_msg
            ));
        }
    }

    Err(format!(
        "Refresh failed for all OAuth clients: {}",
        attempt_errors.join(" | ")
    ))
}