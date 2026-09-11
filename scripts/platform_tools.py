"""Cross-platform discovery with explicit, non-fallback config precedence."""
from __future__ import annotations
import os, platform, shutil
from pathlib import Path


def _existing_file(value):
    if not value:
        return None
    p = Path(value).expanduser()
    return p if p.is_file() else None


def candidate_bash_paths(env=None):
    env = os.environ if env is None else env
    candidates = [env.get("HERMES_GIT_BASH_PATH")]
    if platform.system() == "Darwin":
        candidates += ["/bin/bash", "/usr/bin/bash"]
    la = env.get("LOCALAPPDATA")
    if la:
        candidates += [str(Path(la) / "hermes/git/usr/bin/bash.exe"), str(Path(la) / "hermes/git/bin/bash.exe")]
    for root in (env.get("ProgramFiles"), env.get("ProgramW6432"), env.get("ProgramFiles(x86)")):
        if root:
            candidates += [str(Path(root) / "Git/usr/bin/bash.exe"), str(Path(root) / "Git/bin/bash.exe")]
    candidates += [shutil.which("bash"), shutil.which("bash.exe")]
    out = []
    for value in candidates:
        p = _existing_file(value)
        if p and p not in out and (p.name == "bash" or p.name.lower() == "bash.exe"):
            out.append(p)
    return out


def discover_git(env=None):
    env = os.environ if env is None else env
    candidates = [shutil.which("git"), shutil.which("git.exe")]
    la = env.get("LOCALAPPDATA")
    if la:
        candidates += [str(Path(la) / "hermes/git/cmd/git.exe"), str(Path(la) / "hermes/git/bin/git.exe")]
    for root in (env.get("ProgramFiles"), env.get("ProgramW6432"), env.get("ProgramFiles(x86)")):
        if root:
            candidates += [str(Path(root) / "Git/cmd/git.exe"), str(Path(root) / "Git/bin/git.exe")]
    for value in candidates:
        p = _existing_file(value)
        if p:
            return p
    return None


def config_candidates(cli=None, env=None, home=None):
    env = os.environ if env is None else env
    home = Path(home or Path.home())
    if cli:
        return [Path(cli)]
    paths = []
    if env.get("AGT_CONFIG_PATH"):
        paths.append(Path(env["AGT_CONFIG_PATH"]))
    if env.get("ABV_DATA_DIR"):
        paths.append(Path(env["ABV_DATA_DIR"]) / "gui_config.json")
    if env.get("AGT_CONFIG_DIR"):
        paths.append(Path(env["AGT_CONFIG_DIR"]) / "gui_config.json")
    paths.append(home / ".antigravity_tools" / "gui_config.json")
    return paths


def select_config(cli=None, env=None, home=None):
    candidates = config_candidates(cli, env, home)
    path = candidates[0]
    if not path.is_file():
        raise FileNotFoundError(f"selected config does not exist: {path}")
    return path


def supported_platform():
    system, machine = platform.system(), platform.machine().lower()
    return (system == "Windows" and machine in {"amd64", "x86_64"}) or (system == "Darwin" and machine in {"arm64", "aarch64"})

if __name__ == "__main__":
    print(f"git={discover_git() or 'missing'}")
    print(f"bash={candidate_bash_paths() or 'missing'}")
