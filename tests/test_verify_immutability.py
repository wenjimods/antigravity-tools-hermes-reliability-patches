"""Exercise the real verifier guard in disposable Git repositories."""
import importlib.util
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('change', ['modify', 'delete', 'add_staged', 'add_untracked', 'untrack', 'rename', 'unchanged_failure'])
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
        elif change == 'add_staged':
            (tmp_path / 'added.txt').write_bytes(b'new')
            git('add', 'added.txt')
        elif change == 'add_untracked':
            (tmp_path / 'added.txt').write_bytes(b'new')
        elif change == 'untrack': git('rm', '--cached', 'tracked.txt')
        elif change == 'rename':
            target.rename(tmp_path / 'renamed.txt')
        raise ExpectedFailure('test failure')
    monkeypatch.setattr(verify, 'scan', failing_scan)
    if change == 'unchanged_failure':
        with pytest.raises(ExpectedFailure): verify.main()
    else:
        with pytest.raises(SystemExit, match='tracked files changed'): verify.main()
    if change == 'modify': assert target.read_bytes() == b'changed'
    elif change == 'delete': assert not target.exists()


def test_normal_verify_preserves_observable_state(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('verify_normal',ROOT/'scripts/verify.py')
    verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
    subprocess.run(['git','init','-q'],cwd=tmp_path,check=True)
    (tmp_path/'tracked.txt').write_bytes(b'tracked')
    subprocess.run(['git','add','tracked.txt'],cwd=tmp_path,check=True)
    (tmp_path/'untracked.txt').write_bytes(b'untracked')
    monkeypatch.setattr(verify,'ROOT',tmp_path)
    # Only workload is stubbed here; real successful main/finally snapshot guard executes.
    monkeypatch.setattr(verify,'scan',lambda:None)
    monkeypatch.setattr(verify,'run',lambda args:None)
    import platform_tools
    monkeypatch.setattr(platform_tools,'candidate_bash_paths',lambda:[Path('bash')])
    before=verify.tracked_state();verify.main();assert verify.tracked_state()==before
