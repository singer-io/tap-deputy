import unittest
import os
import json
from tap_deputy.client import DeputyClient
from unittest import mock
from singer.utils import now, strftime, strptime_to_utc
from datetime import timedelta


test_config = {
    "client_id": "client_id",
    "client_secret": "client_secret",
    "domiain": "domain",
    "start_date": "2021-09-20T00:00:00Z",
    "redirect_uri": "redirect_uri",
    "refresh_token": "old_refresh_token",
    "access_token": "old_access_token",
    "expires_at": strftime(now())
}
test_config_path = "/tmp/test_config.json"


def write_new_config_file():
    with open(test_config_path, 'w') as config:
        # Reset tokens while writing the test config
        test_config["refresh_token"] = "old_refresh_token"
        test_config["access_token"] = "old_access_token"
        config.write(json.dumps(test_config))


class TestDevMode(unittest.TestCase):
    def tearDown(self):
        if os.path.isfile(test_config_path):
            os.remove(test_config_path)

    @mock.patch('json.dump')
    @mock.patch('tap_deputy.client.DeputyClient.post')
    def test_dev_mode_not_enabled_expired_token(self, mocked_request, mocked_json_dump):
        test_config["expires_at"] = strftime(now() - timedelta(days=1))
        write_new_config_file()
        deputy = DeputyClient(config=test_config,
                              config_path=test_config_path, dev_mode=False)
        old_expiry_date = test_config["expires_at"]
        mocked_request.return_value = {
            "refresh_token": "new_refresh_token",
            "access_token": "new_access_token",
            "expires_in": 86400
        }
        deputy.refresh()

        self.assertEqual(deputy.refresh_token, "new_refresh_token")
        self.assertEqual(deputy.access_token, "new_access_token")
        self.assertGreater(deputy.expires_at, strptime_to_utc(old_expiry_date))

    @mock.patch('tap_deputy.client.DeputyClient.post')
    def test_dev_mode_not_enabled_valid_token(self, mocked_request):
        """Verify that in dev mode token validation succeeds with token is not expired"""
        test_config["expires_at"] = strftime(now() + timedelta(days=1))
        old_expiry_date = test_config["expires_at"]
        write_new_config_file()
        deputy = DeputyClient(config=test_config,
                              config_path=test_config_path, dev_mode=False)
        self.assertIsNone(deputy.refresh())
        self.assertEqual(deputy.refresh_token, "old_refresh_token")
        self.assertEqual(deputy.access_token, "old_access_token")
        self.assertEqual(deputy.expires_at, strptime_to_utc(old_expiry_date))

    def test_dev_mode_enabled_valid_token(self):
        """Verify that in dev mode token validation succeeds with token is not expired"""
        test_config["expires_at"] = strftime(now() + timedelta(days=1))
        write_new_config_file()
        deputy = DeputyClient(config=test_config,
                              config_path=test_config_path, dev_mode=True)
        self.assertIsNone(deputy.refresh())
        self.assertEqual(deputy.refresh_token, "old_refresh_token")
        self.assertEqual(deputy.access_token, "old_access_token")
