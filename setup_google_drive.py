"""Run locally on your own computer, never in Actions or a shared terminal."""
import pathlib


def main():
    from google_auth_oauthlib.flow import InstalledAppFlow
    folder = pathlib.Path('private_google')
    client = folder / 'client_secret.json'
    if not client.exists():
        raise SystemExit('Save your Desktop OAuth client JSON as private_google/client_secret.json first.')
    # Existing folder was created by a different app. drive.file alone cannot see it.
    # Explain broad scope in setup documentation before the user consents.
    flow = InstalledAppFlow.from_client_secrets_file(
        str(client), scopes=['https://www.googleapis.com/auth/drive'])
    credentials = flow.run_local_server(port=0, access_type='offline', prompt='consent')
    if not credentials.refresh_token:
        raise SystemExit('No refresh token returned; authorization incomplete.')
    target = folder / 'github_drive_auth.json'
    target.write_text(credentials.to_json(), encoding='utf-8')
    target.chmod(0o600)
    print('Authorization saved locally. Add its contents as GitHub Actions secret GOOGLE_DRIVE_AUTH_JSON.')
    print('Do not send this file in chat or commit it to GitHub.')


if __name__ == '__main__':
    main()
