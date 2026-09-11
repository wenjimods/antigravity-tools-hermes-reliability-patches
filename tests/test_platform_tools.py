import os, pathlib, tempfile, unittest
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from platform_tools import config_candidates, select_config, candidate_bash_paths, discover_git
class TestPlatformTools(unittest.TestCase):
 def test_abv_precedes_agt_dir_and_home(self):
  with tempfile.TemporaryDirectory() as d:
   e={'ABV_DATA_DIR':d+'/abv','AGT_CONFIG_DIR':d+'/agt'}; pathlib.Path(e['AGT_CONFIG_DIR']).mkdir(); pathlib.Path(e['ABV_DATA_DIR']).mkdir();
   for x in (e['ABV_DATA_DIR'],e['AGT_CONFIG_DIR']): pathlib.Path(x,'gui_config.json').write_text('{}')
   self.assertEqual(select_config(env=e,home=d),pathlib.Path(e['ABV_DATA_DIR'])/'gui_config.json')
 def test_cli_and_env_precedence(self):
  e={'AGT_CONFIG_PATH':'env.json'}; self.assertEqual(config_candidates('cli.json',e)[0],pathlib.Path('cli.json')); self.assertEqual(config_candidates(None,e)[0],pathlib.Path('env.json'))
 def test_bash_explicit_and_git_path(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'bash.exe'; p.write_bytes(b''); self.assertEqual(candidate_bash_paths({'HERMES_GIT_BASH_PATH':str(p)})[0],p)
if __name__=='__main__': unittest.main()
