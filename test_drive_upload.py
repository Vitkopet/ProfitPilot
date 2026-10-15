import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import drive_upload as drive


class UploadTests(unittest.TestCase):
    def test_missing_secret_is_explicit_and_no_network(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                with patch.dict(os.environ, {'GOOGLE_DRIVE_AUTH_JSON': ''}), patch.object(drive, 'request') as network:
                    self.assertEqual(drive.main(), 0)
                    network.assert_not_called()
                self.assertEqual(json.loads(pathlib.Path('reports/drive_status.json').read_text())['status'],
                                 'AWAITING_GOOGLE_AUTHORIZATION')
            finally:
                os.chdir(old)

    def test_new_upload_and_readback(self):
        responses = [dict(mimeType='application/vnd.google-apps.folder', capabilities=dict(canAddChildren=True)),
                     dict(files=[]), dict(id='file123'), dict(parents=[drive.FOLDER], size='2')]
        with patch.object(drive, 'request', side_effect=responses) as call:
            self.assertEqual(drive.upload(b'{}', '123', 'token'), 'file123')
            self.assertIn('multipart', call.call_args_list[2].args[0])

    def test_rerun_updates_existing_file(self):
        responses = [dict(mimeType='application/vnd.google-apps.folder', capabilities=dict(canAddChildren=True)),
                     dict(files=[dict(id='file123')]), dict(id='file123'),
                     dict(parents=[drive.FOLDER], size='2')]
        with patch.object(drive, 'request', side_effect=responses) as call:
            drive.upload(b'{}', '123', 'token')
            self.assertEqual(call.call_args_list[2].args[3], 'PATCH')

    def test_verification_failure_is_error(self):
        responses = [dict(mimeType='application/vnd.google-apps.folder', capabilities=dict(canAddChildren=True)),
                     dict(files=[]), dict(id='file123'), dict(parents=['wrong'], size='2')]
        with patch.object(drive, 'request', side_effect=responses), self.assertRaises(RuntimeError):
            drive.upload(b'{}', '123', 'token')

    def test_missing_credentials_rejected(self):
        with self.assertRaises(ValueError):
            drive.access_token({})
