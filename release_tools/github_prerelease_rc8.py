"""Publish the approved RC8 artifacts using existing Git credential-manager auth.

Credentials stay in memory and are never logged or written to files.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request

REPO = 'mattmab/ClairObscurSDK'
API = 'https://api.github.com/repos/' + REPO
TAG = 'v0.1.0-rc8'
ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'dist/rc8-candidate'


def token():
    env = dict(os.environ, GCM_INTERACTIVE='Never', GIT_TERMINAL_PROMPT='0')
    result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                            text=True, capture_output=True, env=env, check=False)
    if result.returncode:
        raise RuntimeError('GitHub credential manager authentication unavailable')
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if not values.get('password'):
        raise RuntimeError('GitHub credential manager returned no credential')
    return values['password']


def request(path='', method='GET', body=None, data=None, content_type='application/json'):
    url = path if path.startswith('https://') else API + path
    if urllib.parse.urlparse(url).hostname not in ('api.github.com', 'uploads.github.com'):
        raise ValueError('Unexpected API host')
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'E33-RC8-release', 'Content-Type': content_type})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def existing():
    return next((r for r in request('/releases?per_page=100') if r['tag_name'] == TAG), None)


def main(command, commit=None):
    release = existing()
    if command == 'inspect':
        repo = request()
        print(json.dumps({'repository': repo['full_name'], 'permissions': repo.get('permissions'),
                          'existing_rc8': None if release is None else {'id': release['id'], 'draft': release['draft'], 'url': release['html_url']},
                          'recent_tags': [r['name'] for r in request('/tags?per_page=5')]}))
        return
    if command == 'prepare':
        if release is None:
            if not commit:
                raise ValueError('Reviewed release commit required')
            release = request('/releases', 'POST', body=dict(tag_name=TAG, target_commitish=commit,
                name='SDK 0.1.0-rc8 â€” World Builder', draft=True, prerelease=True,
                body=(ARTIFACTS / 'GITHUB_RELEASE.md').read_text(encoding='utf8')))
        if not release['draft']:
            raise RuntimeError('RC8 already published; refusing to replace release assets')
        files = list(sorted(ARTIFACTS.glob('*.zip'))) + [ARTIFACTS / 'SHA256SUMS.txt', ARTIFACTS / 'VALIDATION.txt']
        present = {a['name']: a for a in request('/releases/' + str(release['id']) + '/assets')}
        for path in files:
            data = path.read_bytes()
            digest = 'sha256:' + hashlib.sha256(data).hexdigest()
            if path.name in present:
                if present[path.name].get('digest') != digest:
                    raise RuntimeError('Existing asset differs: ' + path.name)
                continue
            url = release['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(path.name)
            result = request(url, 'POST', data=data, content_type='application/octet-stream')
            if result['size'] != len(data) or result.get('digest') != digest:
                raise RuntimeError('Uploaded artifact mismatch: ' + path.name)
            print(json.dumps({'uploaded': path.name, 'bytes': result['size'], 'digest': result['digest']}), flush=True)
    elif command == 'publish':
        if release is None or not release['draft']:
            raise RuntimeError('Expected prepared draft RC8')
        assets = request('/releases/' + str(release['id']) + '/assets')
        expected = {p.name: 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in list(ARTIFACTS.glob('*.zip')) + [ARTIFACTS / 'SHA256SUMS.txt', ARTIFACTS / 'VALIDATION.txt']}
        if {a['name']: a.get('digest') for a in assets} != expected:
            raise RuntimeError('Release attachments do not match verified artifacts')
        release = request('/releases/' + str(release['id']), 'PATCH', body=dict(draft=False, prerelease=True, make_latest='false'))
    elif command != 'verify':
        raise ValueError(command)
    release = request('/releases/' + str(release['id']))
    print(json.dumps({'id': release['id'], 'url': release['html_url'], 'draft': release['draft'],
                      'prerelease': release['prerelease'], 'tag': release['tag_name'],
                      'assets': [{'name': a['name'], 'bytes': a['size'], 'digest': a.get('digest')} for a in release['assets']]}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('inspect', 'prepare', 'publish', 'verify'))
    parser.add_argument('--commit')
    args = parser.parse_args()
    TOKEN = token()
    main(args.command, args.commit)
