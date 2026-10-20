#!/usr/bin/env python3
"""Deploy Firebase Hosting with the signed-in gcloud identity. No saved API key.

Run from the repository: python3 deploy/firebase-hosting.py --project YOUR_PROJECT
Builds web/ first. Use --skip-build only after a successful unchanged build.
The Cloud Run service referenced in firebase.json must already exist.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = 'https://firebasehosting.googleapis.com/v1beta1/'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--site', help='Use another globally unique Firebase site name')
    parser.add_argument('--skip-build', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT / 'firebase.json').read_text())['hosting']
    site = args.site or config['site']
    if not args.skip_build:
        subprocess.run(['npm', 'ci'], cwd=ROOT / 'web', check=True)
        subprocess.run(['npm', 'run', 'build'], cwd=ROOT / 'web', check=True)
    public = (ROOT / config['public']).resolve()
    if not (public / 'index.html').is_file():
        raise RuntimeError('Frontend build is missing index.html')
    token = subprocess.run(['gcloud', 'auth', 'print-access-token'], check=True, capture_output=True, text=True).stdout.strip()
    def request(method, url, body=None, raw=None):
        if not url.startswith('https://') or urllib.parse.urlparse(url).hostname not in {'firebasehosting.googleapis.com', 'upload-firebasehosting.googleapis.com'}:
            raise ValueError('Unexpected deployment endpoint')
        payload = raw if raw is not None else json.dumps(body).encode() if body is not None else None
        headers = {'Authorization': 'Bearer ' + token, 'x-goog-user-project': args.project,
                   'Content-Type': 'application/octet-stream' if raw is not None else 'application/json'}
        req = urllib.request.Request(url, data=payload, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            content = response.read()
            return json.loads(content) if content else {}
    try:
        request('GET', API + f'projects/{args.project}/sites/{site}')
    except urllib.error.HTTPError as error:
        if error.code != 404: raise
        request('POST', API + f'projects/{args.project}/sites?siteId={site}', {})
    headers = [{'glob': row['source'], 'headers': {h['key']: h['value'] for h in row['headers']}} for row in config.get('headers', [])]
    rewrites = []
    for row in config['rewrites']:
        item = {'glob': row['source']}
        if 'run' in row: item['run'] = row['run']
        else: item['path'] = row['destination']
        rewrites.append(item)
    version = request('POST', API + f'sites/{site}/versions', {'config': {'headers': headers, 'rewrites': rewrites}})['name']
    blobs, files = {}, {}
    for path in sorted(public.rglob('*')):
        if not path.is_file() or path.is_symlink() or any(part.startswith('.') for part in path.relative_to(public).parts): continue
        compressed = gzip.compress(path.read_bytes(), mtime=0)
        digest = hashlib.sha256(compressed).hexdigest()
        files['/' + path.relative_to(public).as_posix()] = digest
        blobs[digest] = compressed
    populated = request('POST', API + version + ':populateFiles', {'files': files})
    for digest in populated.get('uploadRequiredHashes', []):
        request('POST', populated['uploadUrl'] + '/' + digest, raw=blobs[digest])
    request('PATCH', API + version + '?update_mask=status', {'status': 'FINALIZED'})
    release = request('POST', API + f'sites/{site}/releases?versionName=' + version, {})
    print(json.dumps({'url': f'https://{site}.web.app', 'version': version,
                      'release': release['name'], 'files': len(files)}, indent=2))

if __name__ == '__main__':
    try: main()
    except urllib.error.HTTPError as error:
        raise SystemExit(f'Firebase deployment failed ({error.code}): {error.read().decode()[:1500]}')
