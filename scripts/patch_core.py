"""Hash-checked, reversible patch application for AGT and Hermes assets."""
import hashlib, json, shutil, subprocess, tempfile
from pathlib import Path
from platform_tools import discover_git


def digest(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _assets(group):
    name = group if group in {"hermes", "agt-4.6.7", "agt-4.7.0"} else f"agt-{group}"
    path = Path(__file__).resolve().parents[1] / "patches" / name
    if not path.is_dir(): raise ValueError(f"unknown patch group: {group}")
    return path


def _safe(root, name):
    root = Path(root).resolve()
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError("unsafe target path")
    path = root / relative
    for part in [path, *path.parents]:
        if part == root: break
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError("unsafe target path")
    if not path.resolve().is_relative_to(root): raise ValueError("unsafe target path")
    return path


def _manifest(assets):
    manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") == "BLOCKED":
        raise ValueError(f"patch group is BLOCKED: {manifest.get('blocked_reason', 'no reason supplied')}")
    if not isinstance(manifest.get("files"), dict) or not manifest.get("patch"):
        raise ValueError("patch group has no usable manifest/patch")
    patch = assets / manifest["patch"]
    if digest(patch.read_bytes()) != manifest["patch_sha256"]: raise ValueError("patch integrity mismatch")
    return manifest, patch


def _state(root, manifest):
    return {name: digest(_safe(root, name).read_bytes()) if _safe(root, name).is_file() else None for name in manifest["files"]}


def _expected(state, manifest, phase):
    return all(state[name] == hashes[phase] for name, hashes in manifest["files"].items())


def _git_apply(temp, patch, reverse=False, check=False):
    git = discover_git()
    if not git: raise RuntimeError("git executable not found")
    args = [str(git), '-c', 'core.autocrlf=false', "apply"]
    if reverse: args.append("--reverse")
    if check: args.append("--check")
    args.append(str(patch))
    return subprocess.run(args, cwd=temp, capture_output=True, text=True)


def _build(root, manifest, patch, reverse=False):
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        for name, hashes in manifest["files"].items():
            source = _safe(root, name)
            if source.is_file():
                target = temp / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
        check = _git_apply(temp, patch, reverse=reverse, check=True)
        if check.returncode: raise RuntimeError(check.stderr.strip() or "git apply check failed")
        done = _git_apply(temp, patch, reverse=reverse)
        if done.returncode: raise RuntimeError(done.stderr.strip() or "git apply failed")
        payload = {name: (temp / name).read_bytes() if (temp / name).is_file() else None for name in manifest["files"]}
        phase = "before" if reverse else "after"
        if not all((payload[name] is None and hashes[phase] is None) or
                   (payload[name] is not None and hashes[phase] is not None and digest(payload[name]) == hashes[phase])
                   for name, hashes in manifest["files"].items()):
            raise RuntimeError("unexpected patch output hash")
        return payload


def _write(root, payload, originals):
    try:
        for name, data in payload.items():
            path = _safe(root, name); path.parent.mkdir(parents=True, exist_ok=True)
            if data is None: path.unlink(missing_ok=True)
            else: path.write_bytes(data)
    except Exception:
        for name, data in originals.items():
            path = _safe(root, name)
            if data is None: path.unlink(missing_ok=True)
            else: path.write_bytes(data)
        raise


def apply(root, group="agt-4.7.0", dry_run=False, version=None):
    group = f"agt-{version}" if version else group
    assets = _assets(group); manifest, patch = _manifest(assets); root = Path(root).resolve(); before = _state(root, manifest)
    if _expected(before, manifest, "after"): print("Already applied: exact complete state"); return True
    if not _expected(before, manifest, "before"): print("ERROR: unknown/partial/modified target; no writes"); return False
    payload = _build(root, manifest, patch)
    if dry_run: print("Dry-run PASS: input, patch, output hashes verified; no writes"); return True
    if _state(root, manifest) != before: print("ERROR: target changed during validation; no writes"); return False
    originals = {name: (_safe(root, name).read_bytes() if _safe(root, name).is_file() else None) for name in payload}
    _write(root, payload, originals)
    if not _expected(_state(root, manifest), manifest, "after"): raise RuntimeError("post-write hash verification failed")
    print("Applied: exact output hashes verified"); return True


def rollback(root, version="4.7.0", dry_run=False):
    group = version if version == "hermes" else f"agt-{version}"
    assets = _assets(group); manifest, patch = _manifest(assets); root = Path(root).resolve(); after = _state(root, manifest)
    if _expected(after, manifest, "before"): print("Already rolled back: exact before state"); return True
    if not _expected(after, manifest, "after"): print("ERROR: rollback requires exact after state; no writes"); return False
    payload = _build(root, manifest, patch, reverse=True)
    if dry_run: print("Rollback dry-run PASS: input, patch, output hashes verified; no writes"); return True
    if _state(root, manifest) != after: print("ERROR: target changed during validation; no writes"); return False
    originals = {name: _safe(root, name).read_bytes() for name in manifest["files"]}
    _write(root, payload, originals)
    if not _expected(_state(root, manifest), manifest, "before"): raise RuntimeError("post-rollback hash verification failed")
    print("Rolled back: exact before hashes verified"); return True
