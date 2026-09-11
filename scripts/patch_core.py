"""Exact file-state patching; validate in scratch before touching a target."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

def digest(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()

def apply(root, group, dry_run=False):
    root = Path(root).resolve()
    assets = Path(__file__).resolve().parents[1] / 'patches' / group
    manifest = json.loads((assets / 'manifest.json').read_text())
    patch = assets / manifest['patch']
    if digest(patch.read_bytes()) != manifest['patch_sha256']:
        print('ERROR: patch integrity mismatch'); return False
    states = {}
    for name in manifest['files']:
        p = root / name
        if p.is_symlink() or not p.resolve().is_relative_to(root):
            print('ERROR: unsafe target path'); return False
        states[name] = digest(p.read_bytes()) if p.is_file() else None
    for state in ('after', 'before'):
        if all(states[n] == h[state] for n, h in manifest['files'].items()):
            break
    else:
        print('ERROR: unknown/partial/modified target; no writes'); return False
    if state == 'after':
        print('Already applied: exact complete state'); return True
    # CRLF source checkouts are normalized only in scratch, not before validation.
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        for name, h in manifest['files'].items():
            if h['before'] is not None:
                p = temp / name; p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes((root / name).read_bytes().replace(b'\r\n', b'\n'))
        subprocess.run(['git', 'init', '-q', str(temp)], check=True)
        for args in (['--check'], []):
            result = subprocess.run(['git', 'apply', *args, str(patch)], cwd=temp, capture_output=True, text=True)
            if result.returncode:
                print(result.stderr); return False
        payload = {n: (temp/n).read_bytes() for n in manifest['files']}
        if not all(digest(payload[n]) == h['after'] for n,h in manifest['files'].items()):
            print('ERROR: unexpected patch output'); return False
        if dry_run:
            print('Dry-run PASS: real patch and output hashes'); return True
        originals = {n: (root/n).read_bytes() if (root/n).exists() else None for n in payload}
        if any((digest(b) if b is not None else None) != states[n] for n,b in originals.items()):
            print('ERROR: target changed during validation'); return False
        try:
            for n,b in payload.items():
                p=root/n; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
        except OSError:
            for n,b in originals.items():
                if b is None: (root/n).unlink(missing_ok=True)
                else: (root/n).write_bytes(b)
            raise
    print('Applied: exact hashes verified'); return True
