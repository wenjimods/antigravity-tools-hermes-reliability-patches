import os
import pathlib
import difflib
import re

def generate_hermes_patch():
    # 1. agent/error_classifier.py
    ec_path = pathlib.Path(os.environ.get('HERMES_ERROR_CLASSIFIER', 'agent/error_classifier.py'))
    ec_orig = ec_path.read_text(encoding='utf-8').replace('\r\n', '\n')

    ec_mod = ec_orig
    anchor1 = '_OVERLOADED_PATTERNS = ('
    addition1 = '''_UPSTREAM_ACCOUNT_LIMITED_PATTERNS = (
    "all accounts limited", "all accounts rate-limited", "all accounts failed",
)

'''
    ec_mod = ec_mod.replace(anchor1, addition1 + anchor1, 1)

    anchor2 = '    503: lambda c: _first_match(c.msg, _OVERFLOW_AS_5XX_RULES) or _V_OVERLOADED,'
    replacement2 = '''    503: lambda c: _first_match(c.msg, _OVERFLOW_AS_5XX_RULES) or (
        _v(_R.upstream_rate_limit, should_fallback=False, error_context=_extract_upstream_wait_context(c.msg))
        if any(p in c.msg for p in _UPSTREAM_ACCOUNT_LIMITED_PATTERNS)
        else _V_OVERLOADED
    ),'''
    ec_mod = ec_mod.replace(anchor2, replacement2, 1)

    anchor3 = '    (_OVERLOADED_PATTERNS, _V_OVERLOADED),'
    replacement3 = '''    (_UPSTREAM_ACCOUNT_LIMITED_PATTERNS, lambda msg: _v(_R.upstream_rate_limit, should_fallback=False, error_context=_extract_upstream_wait_context(msg))),
    (_OVERLOADED_PATTERNS, _V_OVERLOADED),'''
    ec_mod = ec_mod.replace(anchor3, replacement3, 1)

    anchor4 = 'def _extract_upstream_provider_name(body: Any) -> Optional[str]:'
    helper_code = '''def _extract_upstream_wait_context(error_msg: str) -> Dict[str, Any]:
    """Extract upstream rate limit wait context (e.g. from AGT 8045 responses)."""
    import re
    match = re.search(r'(?:wait|resets?\\s+in|retry\\s+after)\\s+(\\d+(?:\\.\\d+)?)\\s*s(?:econds?)?', error_msg, re.IGNORECASE)
    ctx: Dict[str, Any] = {"upstream_provider": "agt"}
    if match:
        try:
            ctx["wait_seconds"] = float(match.group(1))
        except (TypeError, ValueError):
            pass
    return ctx


'''
    ec_mod = ec_mod.replace(anchor4, helper_code + anchor4, 1)

    # 2. agent/retry_utils.py
    ru_path = pathlib.Path(os.environ.get('HERMES_RETRY_UTILS', 'agent/retry_utils.py'))
    ru_orig = ru_path.read_text(encoding='utf-8').replace('\r\n', '\n')

    ru_mod = ru_orig
    anchor_ru = 'def is_zai_coding_overload_error('
    func_ru = '''def parse_upstream_wait_seconds(error_or_text: Any) -> Optional[float]:
    """Parse wait duration from upstream rate limit messages like 'All accounts limited. Wait 12s.'"""
    if error_or_text is None:
        return None
    import re
    text = _error_text(error_or_text) if not isinstance(error_or_text, str) else error_or_text.lower()
    match = re.search(r'(?:wait|resets?\\s+in|retry\\s+after)\\s+(\\d+(?:\\.\\d+)?)\\s*s(?:econds?)?', text, re.IGNORECASE)
    if match:
        try:
            return max(0.0, float(match.group(1)))
        except (TypeError, ValueError):
            pass
    return None


'''
    ru_mod = ru_mod.replace(anchor_ru, func_ru + anchor_ru, 1)

    # 3. agent/turn_recovery.py
    tr_path = pathlib.Path(os.environ.get('HERMES_TURN_RECOVERY', 'agent/turn_recovery.py'))
    tr_orig = tr_path.read_text(encoding='utf-8').replace('\r\n', '\n')

    tr_mod = tr_orig
    anchor_tr = 'from agent.retry_utils import adaptive_rate_limit_backoff, jittered_backoff, parse_retry_after_seconds'
    replacement_tr = 'from agent.retry_utils import adaptive_rate_limit_backoff, jittered_backoff, parse_retry_after_seconds, parse_upstream_wait_seconds'
    tr_mod = tr_mod.replace(anchor_tr, replacement_tr, 1)

    anchor_tr2 = '    wait_time = _retry_after if _retry_after is not None else jittered_backoff(retry_count, base_delay=2.0, max_delay=60.0)'
    replacement_tr2 = '''    # AGT upstream account pool rate limit ('all accounts limited. wait Ns') -> wait N+1 seconds
    _upstream_wait = parse_upstream_wait_seconds(api_error)
    if _upstream_wait is not None and ('all accounts limited' in str(api_error).lower() or getattr(classified, 'reason', None) == FailoverReason.upstream_rate_limit):
        _retry_after = min(_upstream_wait + 1.0, 600.0)

    wait_time = _retry_after if _retry_after is not None else jittered_backoff(retry_count, base_delay=2.0, max_delay=60.0)'''
    tr_mod = tr_mod.replace(anchor_tr2, replacement_tr2, 1)

    diff_ec = list(difflib.unified_diff(
        ec_orig.splitlines(keepends=True),
        ec_mod.splitlines(keepends=True),
        fromfile='a/agent/error_classifier.py',
        tofile='b/agent/error_classifier.py'
    ))
    diff_ru = list(difflib.unified_diff(
        ru_orig.splitlines(keepends=True),
        ru_mod.splitlines(keepends=True),
        fromfile='a/agent/retry_utils.py',
        tofile='b/agent/retry_utils.py'
    ))
    diff_tr = list(difflib.unified_diff(
        tr_orig.splitlines(keepends=True),
        tr_mod.splitlines(keepends=True),
        fromfile='a/agent/turn_recovery.py',
        tofile='b/agent/turn_recovery.py'
    ))

    full_hermes_patch = ''.join(diff_ec) + ''.join(diff_ru) + ''.join(diff_tr)
    out_hermes_file = pathlib.Path(os.environ.get('HERMES_PATCH_OUTPUT', 'patches/hermes/hermes-all-accounts-limited-retry.patch'))
    out_hermes_file.parent.mkdir(parents=True, exist_ok=True)
    out_hermes_file.write_text(full_hermes_patch, encoding='utf-8')
    print('Wrote hermes-all-accounts-limited-retry.patch, total bytes:', len(full_hermes_patch))

if __name__ == '__main__':
    generate_hermes_patch()
