"""Real patch operations on tarball-like directories with read-only evidence."""
from pathlib import Path
import json
import shutil
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import patch_core as core
A=ROOT/'patches/agt-4.7.0'
E='src-tauri/src/modules/oauth.rs'

def snapshot(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}

@pytest.mark.parametrize('phase',['before','after','rolled_back'])
@pytest.mark.parametrize('mutation',['missing','modified'])
def test_evidence_mismatch_closed_for_apply_and_rollback(tmp_path,phase,mutation):
    shutil.copytree(A/'baseline',tmp_path,dirs_exist_ok=True)
    assert not (tmp_path/'.git').exists()
    if phase!='before': assert core.apply(tmp_path)
    if phase=='rolled_back': assert core.rollback(tmp_path)
    evidence=tmp_path/E
    if mutation=='missing': evidence.unlink()
    else: evidence.write_bytes(evidence.read_bytes()+b'// semantic change\n')
    before=snapshot(tmp_path)
    for action in [lambda:core.apply(tmp_path,dry_run=True),lambda:core.apply(tmp_path),lambda:core.rollback(tmp_path,dry_run=True),lambda:core.rollback(tmp_path)]:
        with pytest.raises(ValueError,match='evidence integrity mismatch'): action()
        assert snapshot(tmp_path)==before

def test_tarball_evidence_untouched_roundtrip(tmp_path):
    shutil.copytree(A/'baseline',tmp_path,dirs_exist_ok=True)
    evidence=(tmp_path/E).read_bytes(); (tmp_path/E).write_bytes(evidence.replace(b'\n',b'\r\n'))
    before=(tmp_path/E).read_bytes()
    for action in [lambda:core.apply(tmp_path,dry_run=True),lambda:core.apply(tmp_path),lambda:core.apply(tmp_path),lambda:core.rollback(tmp_path,dry_run=True),lambda:core.rollback(tmp_path),lambda:core.rollback(tmp_path)]:
        assert action(); assert (tmp_path/E).read_bytes()==before
    assert not (tmp_path/'src-tauri/src/proxy/refresh_budget.rs').exists()

@pytest.mark.parametrize('name',['../outside.rs','/absolute.rs'])
def test_evidence_path_rejected(tmp_path,name):
    with pytest.raises(ValueError,match='unsafe'):
        core._check_evidence(tmp_path,{'evidence_files':{name:'0'*64}})

def test_evidence_target_overlap_rejected(tmp_path):
    manifest=json.loads((A/'manifest.json').read_text());n=next(iter(manifest['files']));manifest['evidence_files']={n:'0'*64}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='also a patch target'): core._manifest(tmp_path)
