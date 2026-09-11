import argparse
from patch_core import apply, rollback

def apply_patch(src_dir, dry_run=False, version='4.7.0'):
    return apply(src_dir, f'agt-{version}', dry_run, version)

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('src_dir'); p.add_argument('--dry-run',action='store_true'); p.add_argument('--version',default='4.7.0'); p.add_argument('--rollback',action='store_true')
    a=p.parse_args()
    try: ok=rollback(a.src_dir,a.version,a.dry_run) if a.rollback else apply_patch(a.src_dir,a.dry_run,a.version)
    except ValueError as e: p.error(str(e))
    raise SystemExit(0 if ok else 1)
