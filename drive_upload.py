"""Archive scan reports to the configured My Drive folder via user OAuth."""
import datetime as dt
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

FOLDER = '1VIdtc5NasgXTuQGBGUPA8MbVWRUncNzx'
API = 'https://www.googleapis.com/drive/v3/files'


def request(url, token=None, data=None, method=None, content_type=None):
    headers = {}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if content_type:
        headers['Content-Type'] = content_type
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Do not print response bodies, credentials or token endpoint requests.
        raise RuntimeError('Google API HTTP ' + str(error.code)) from None
    except urllib.error.URLError:
        raise RuntimeError('Google API network error') from None


def access_token(credentials):
    required = ('client_id', 'client_secret', 'refresh_token')
    if any(not isinstance(credentials.get(k), str) or not credentials[k] for k in required):
        raise ValueError('OAuth JSON requires client_id, client_secret and refresh_token')
    body = urllib.parse.urlencode({**{k: credentials[k] for k in required},
                                   'grant_type': 'refresh_token'}).encode()
    result = request('https://oauth2.googleapis.com/token', data=body,
                     content_type='application/x-www-form-urlencoded')
    token = result.get('access_token')
    if not isinstance(token, str) or not token:
        raise RuntimeError('Google did not return an access token')
    return token


def upload(report, run_id, token):
    if not re.fullmatch(r'[0-9]+', run_id):
        raise ValueError('Expected numeric GitHub run id')
    folder = request(API + '/' + FOLDER + '?fields=id,mimeType,trashed,capabilities(canAddChildren)', token)
    if (folder.get('mimeType') != 'application/vnd.google-apps.folder'
            or folder.get('trashed') or not folder.get('capabilities', {}).get('canAddChildren')):
        raise RuntimeError('Target folder is unavailable or not writable')
    name = 'acceleration-' + run_id + '.json'
    query = urllib.parse.urlencode(dict(q=f"'{FOLDER}' in parents and name = '{name}' and trashed = false",
                                        fields='files(id)', pageSize=2))
    matches = request(API + '?' + query, token).get('files', [])
    if len(matches) > 1:
        raise RuntimeError('Duplicate archive names; refusing ambiguous update')
    if matches:
        # Rerunning the same GitHub run updates its report, avoiding duplicates.
        result = request('https://www.googleapis.com/upload/drive/v3/files/'
                         + matches[0]['id'] + '?uploadType=media&fields=id',
                         token, report, 'PATCH', 'application/json')
    else:
        boundary = 'aich_' + uuid.uuid4().hex
        metadata = json.dumps(dict(name=name, parents=[FOLDER], mimeType='application/json')).encode()
        body = (f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'.encode()
                + metadata + f'\r\n--{boundary}\r\nContent-Type: application/json\r\n\r\n'.encode()
                + report + f'\r\n--{boundary}--\r\n'.encode())
        result = request('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id',
                         token, body, 'POST', 'multipart/related; boundary=' + boundary)
    if not result.get('id'):
        raise RuntimeError('Upload response missing file id')
    confirmed = request(API + '/' + result['id'] + '?fields=id,name,parents,size', token)
    if FOLDER not in confirmed.get('parents', []) or int(confirmed.get('size', -1)) != len(report):
        raise RuntimeError('Uploaded file verification failed')
    return result['id']


def main():
    output = pathlib.Path('reports')
    output.mkdir(exist_ok=True)
    status = dict(checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    code = 0
    try:
        secret = os.environ.get('GOOGLE_DRIVE_AUTH_JSON', '')
        if not secret:
            status['status'] = 'AWAITING_GOOGLE_AUTHORIZATION'
            print('::warning::Drive archive awaits GOOGLE_DRIVE_AUTH_JSON secret; GitHub artifacts remain active.')
        elif not (output / 'latest.json').exists():
            status['status'] = 'NO_REPORT'
            raise RuntimeError('No scan report available for upload')
        else:
            credentials = json.loads(secret)
            report = (output / 'latest.json').read_bytes()
            json.loads(report)  # Refuse invalid JSON before contacting Drive.
            status['file_id'] = upload(report, os.environ.get('GITHUB_RUN_ID', ''), access_token(credentials))
            status['status'] = 'UPLOADED_AND_VERIFIED'
            print('Drive report uploaded and verified.')
    except Exception as error:
        status['status'] = 'UPLOAD_FAILED'
        # Only controlled error text is safe to log; malformed JSON may contain secrets.
        status['error_type'] = type(error).__name__
        print('::error::Drive upload failed (' + type(error).__name__ + '); report retained in GitHub artifacts.')
        code = 1
    (output / 'drive_status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    return code


if __name__ == '__main__':
    sys.exit(main())
