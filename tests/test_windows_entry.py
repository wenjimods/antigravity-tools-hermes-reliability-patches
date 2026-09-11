import json,os,shutil,subprocess,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1]
@pytest.mark.skipif(sys.platform!='win32',reason='Native Windows PowerShell test')
def test_native_windows_entry(tmp_path):
 root=tmp_path/'中文 空格';root.mkdir();src=root/'源码';shutil.copytree(R/'patches/agt-4.7.0/baseline',src)
 cfg=root/'gui_config.json';cfg.write_text(json.dumps(dict(language='zh',theme='system',auto_refresh=True,refresh_interval=15,auto_sync=False,sync_interval=5)))
 original=cfg.read_bytes(); token=src/'src-tauri/src/proxy/token_manager.rs'; b=token.read_bytes()
 env=os.environ.copy();env['PATH']=str(Path(sys.executable).parent)+os.pathsep+env['PATH'];env['PYTHONIOENCODING']='utf-8'
 command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'scripts/setup_windows.ps1'),'-SourceDir',str(src),'-Config',str(cfg),'-Version','4.7.0']
 def run(extra=[]):return subprocess.run(command+extra,env=env,capture_output=True,timeout=45)
 result=run();assert result.returncode==0,result.stdout+result.stderr
 assert cfg.read_bytes()==original and token.read_bytes()==b
 result=run(['-Apply']);assert result.returncode==0,result.stdout+result.stderr
 assert token.read_bytes()!=b and json.loads(cfg.read_bytes())['refresh_interval']==2
 token.write_bytes(b'unknown version');snap=cfg.read_bytes()
 result=run(['-Apply']);assert result.returncode!=0
 assert cfg.read_bytes()==snap
