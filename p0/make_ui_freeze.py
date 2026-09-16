"""Generate p0/ui-freeze.json (P0-B §26).

Seals: git SHA, app code, review schema, protocol, sample, assignments,
candidate/graph engine SHAs. After this file exists, product logic is
frozen until P0-D completes.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SEALED = {
    'review_schema': 'p0/manifests/review-schema.json',
    'protocol': 'p0/manifests/protocol.json',
    'sample': 'p0/manifests/sample.json',
    'assignments': 'p0/manifests/assignments.json',
    'app_models': 'p0/app/models.py',
    'app_cases': 'p0/app/cases.py',
    'app_store': 'p0/app/store.py',
    'app_evidence': 'p0/app/evidence.py',
    'app_session': 'p0/app/session.py',
    'app_server': 'p0/app/server.py',
    'app_js': 'p0/app/static/app.js',
    'app_css': 'p0/app/static/style.css',
    'app_html': 'p0/app/static/index.html',
    'ingest': 'p0/ingest_p0.py',
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', type=int, default=1)
    ap.add_argument('--purpose', default='PRE_WARMUP')
    ap.add_argument('--out', default='p0/ui-freeze.json')
    ap.add_argument('--supersedes', default=None)
    args = ap.parse_args()

    git_sha = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    tree_sha = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD^{tree}'], cwd=REPO, text=True).strip()
    files = {}
    for name, rel in SEALED.items():
        p = REPO / rel
        files[name] = {'path': rel, 'sha256': sha(p) if p.exists()
                       else None}
    # engine SHAs: frozen extraction/graph modules
    engines = {
        'candidate_engine': 'src/emissions_es/extraction',
        'graph_engine': 'src/emissions_es/linking',
    }
    for name, rel in engines.items():
        h = hashlib.sha256()
        for f in sorted((REPO / rel).rglob('*.py')):
            h.update(f.name.encode())
            h.update(f.read_bytes())
        files[name] = {'path': rel + '/', 'sha256': h.hexdigest()}

    tests = subprocess.run(
        [sys.executable, '-m', 'pytest', 'tests/test_p0_app.py', '-x', '-q'],
        cwd=REPO, capture_output=True, text=True)
    out = {'manifest': 'p0-ui-freeze',
           'freeze_version': args.version,
           'purpose': args.purpose,
           'supersedes': args.supersedes,
           'frozen_at': datetime.now(timezone.utc)
           .isoformat(timespec='seconds'),
           'git_sha': git_sha, 'tree_sha': tree_sha,
           'tests': {'suite': 'tests/test_p0_app.py',
                     'returncode': tests.returncode,
                     'tail': tests.stdout.strip().splitlines()[-1:]
                     if tests.stdout else []},
           'files': files}
    (REPO / args.out).write_text(json.dumps(out, indent=1))
    print(f'ui-freeze v{args.version} ({args.purpose}) -> {args.out} '
          f'at {git_sha[:10]}, tests rc={tests.returncode}')


if __name__ == '__main__':
    main()
