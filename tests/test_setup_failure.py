"""Execute real setup+patch; replace only configuration writer with explicit failure stub."""
import os
from pathlib import Path
import subprocess
import shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('shell',['bash','powershell'])
@pytest.mark.parametrize('apply_mode',[False,True])
def test_configuration_failure_after_real_source_apply(tmp_path,shell,apply_mode):
    if shell=='powershell' and shutil.which('powershell.exe') is None: pytest.skip('native PowerShell unavailable')
    kit=tmp_path/'kit space'
    shutil.copytree(ROOT/'scripts',kit/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'patches/agt-4.7.0',kit/'patches/agt-4.7.0',ignore=shutil.ignore_patterns('target'))
    src=tmp_path/'source space';shutil.copytree(ROOT/'patches/agt-4.7.0/baseline',src)
    cfg=tmp_path/'config.json';cfg.write_text('{}')
    stub=kit/'configs/agt/apply_refresh_interval.py';stub.parent.mkdir(parents=True)
    stub.write_text('import sys\n# Synthetic config writer: preflight succeeds, write fails.\nsys.exit(0 if "--dry-run" in sys.argv else 37)\n')
    env={**os.environ,'PYTHON':os.sys.executable}
    # Git Bash needs normal native argv conversion; Hermes terminal disables it globally.
    env.pop('MSYS_NO_PATHCONV',None);env.pop('MSYS2_ARG_CONV_EXCL',None)
    if shell=='powershell':
        cmd=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(kit/'scripts/setup_windows.ps1'),'-SourceDir',str(src),'-Config',str(cfg)]
        if apply_mode:cmd+=['-Apply']
    else:
        cmd=[shutil.which('bash') or '/bin/bash',str(kit/'scripts/setup_macos.sh'),str(src),'--config',str(cfg)]
        if apply_mode:cmd+=['--apply']
    result=subprocess.run(cmd,capture_output=True,env=env,timeout=60)
    output=result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace')
    helper=src/'src-tauri/src/proxy/refresh_budget.rs'
    if apply_mode:
        assert result.returncode!=0,output
        assert 'AGT source patch has already been applied; configuration update failed.' in output,output
        assert helper.exists(),output
    else:
        assert result.returncode==0,output
        assert not helper.exists()
    assert cfg.read_text()=='{}'
