"""Exercise the real verifier guard in disposable Git repositories."""
import importlib.util
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('change', ['modify', 'delete', 'add', 'untrack', 'unchanged_failure'])
def test_finally_checks_tracked_state_without_restoring(tmp_path, monkeypatch, change):
    spec = importlib.util.spec_from_file_location('verify_probe', ROOT / 'scripts/verify.py')
    verify = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verify)
    def git(*args):
        subprocess.run(['git', *args], cwd=tmp_path, check=True, capture_output=True)
    git('init', '-q')
    target = tmp_path / 'tracked.txt'
    target.write_bytes(b'original')
    git('add', 'tracked.txt')
    monkeypatch.setattr(verify, 'ROOT', tmp_path)
    class ExpectedFailure(Exception):
        pass
    def failing_scan():
        if change == 'modify': target.write_bytes(b'changed')
        elif change == 'delete': target.unlink()
        elif change == 'add':
            (tmp_path / 'added.txt').write_bytes(b'new')
            git('add', 'added.txt')
        elif change == 'untrack': git('rm', '--cached', 'tracked.txt')
        raise ExpectedFailure('test failure')
    monkeypatch.setattr(verify, 'scan', failing_scan)
    if change == 'unchanged_failure':
        with pytest.raises(ExpectedFailure): verify.main()
    else:
        with pytest.raises(SystemExit, match='tracked files changed'): verify.main()
    if change == 'modify': assert target.read_bytes() == b'changed'
    elif change == 'delete': assert not target.exists()
