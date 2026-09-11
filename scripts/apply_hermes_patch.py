import argparse
from patch_core import apply

def apply_patch(src_dir, dry_run=False):
    return apply(src_dir, 'hermes', dry_run)

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('src_dir'); p.add_argument('--dry-run',action='store_true')
    a=p.parse_args(); raise SystemExit(0 if apply_patch(a.src_dir,a.dry_run) else 1)
