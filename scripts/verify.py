"""Offline acceptance entry point; never contacts or changes a live service."""
from pathlib import Path
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True, stdin=subprocess.DEVNULL)


def tracked_state():
    cached = [n for n in subprocess.check_output(['git', 'ls-files', '--cached', '-z'], cwd=ROOT).decode().split('\0') if n]
    others = [n for n in subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0') if n]
    state = {}
    for kind, names in (("tracked", cached), ("untracked", others)):
        for name in names:
            path = ROOT / name
            state[(kind, name)] = (path.exists(), hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None)
    # Retain tracked paths that disappeared from the worktree.
    for name in [n for n in subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode().split('\0') if n]:
        state.setdefault(("tracked", name), (False, None))
    return state


def scan():
    # Scan tracked AND new non-ignored files, plus every reachable Git blob.
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    files = sorted({n for n in names if n and (ROOT / n).is_file()})
    patterns = {
        'private-key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'google-key': rb'AIza[0-9A-Za-z_-]{35}',
        'github-token': rb'gh[pousr]_[A-Za-z0-9]{30,}',
        'openai-key': rb'sk-(?:proj-)?[A-Za-z0-9_-]{30,}',
        'jwt': rb'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',
        'private-machine-path': rb'(?:[A-Z]:[\\/]Users[\\/](?!<)[A-Za-z0-9_-]+|/Users/(?!<)[A-Za-z0-9_-]+)',
    }
    failures = []
    def inspect(label, data):
        for kind, pattern in patterns.items():
            if re.search(pattern, data):
                failures.append(f'{label}: {kind}')
    for name in files:
        data = (ROOT / name).read_bytes()
        inspect(name, data)
        p = Path(name)
        if p.suffix.lower() in {'.exe', '.dll', '.db', '.sqlite', '.sqlite3', '.log', '.pem', '.key', '.zip'} or p.name in {'accounts.json', 'gui_config.json', '.env'}:
            failures.append(f'{name}: forbidden runtime artifact')
        if p.suffix == '.py':
            ast.parse(data.decode('utf-8-sig'), filename=name)
        elif p.suffix == '.json' or name.endswith('.json.template'):
            json.loads(data.decode('utf-8-sig'))
    objects = subprocess.check_output(['git', 'rev-list', '--objects', '--all'], cwd=ROOT).decode().splitlines()
    blobs = 0
    for entry in objects:
        oid = entry.split(' ', 1)[0]
        if subprocess.check_output(['git', 'cat-file', '-t', oid], cwd=ROOT).strip() == b'blob':
            blobs += 1
            inspect('history:' + oid, subprocess.check_output(['git', 'cat-file', 'blob', oid], cwd=ROOT))
    print(f'Scanned {len(files)} files and {blobs} historical blobs (pattern-based, not a guarantee).')
    if failures:
        raise SystemExit('\n'.join(failures))
    print('Syntax/JSON and secret/path pattern scan: PASS')


def main():
    before = tracked_state()
    try:
        scan()
        run([sys.executable, '-m', 'pytest', '-q', 'tests'])
        run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
        from platform_tools import candidate_bash_paths
        candidates = candidate_bash_paths()
        bash = str(candidates[0]) if candidates else None
        if not bash: raise SystemExit('bash required for shell syntax acceptance')
        for script in sorted((ROOT / 'scripts').glob('*.sh')): run([bash, '-n', script])
        for harness in sorted((ROOT / 'patches').glob('agt-*/harness/Cargo.toml')):
            if shutil.which('cargo') is None: raise SystemExit('cargo required by harness manifest')
            try: run(['cargo', 'fetch', '--manifest-path', harness])
            except subprocess.CalledProcessError as exc: raise SystemExit('cargo fetch failed; offline harness not run') from exc
            run(['cargo', 'test', '--offline', '--manifest-path', harness])
    finally:
        after = tracked_state()
        if before != after:
            added = sorted(set(after) - set(before)); removed = sorted(set(before) - set(after))
            changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
            raise SystemExit(f'tracked files changed (no auto-restore): added={added}, removed={removed}, changed={changed}')
    print('Offline checks: PASS. This does NOT prove macOS build or live API operation.')


if __name__ == '__main__':
    main()
