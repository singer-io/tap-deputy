from distutils.command.config import config
from genericpath import isfile
import unittest
import os, json
from tap_deputy.client import DeputyClient
from tap_deputy.utils import write_config
from unittest import mock
from singer.utils import strftime
from singer.utils import now, strftime, strptime_to_utc
from dateutil.parser import parse
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
       config.write(json.dumps(test_config))

def tear_down():
    if os.path.isfile(test_config_path):
        os.remove(test_config_path)
    
    if os.path.isfile(test_config_path):
        os.remove(test_config_path)

class TestDevMode(unittest.TestCase):
    @mock.patch('json.dump')
    @mock.patch('tap_deputy.utils.write_config', side_effect=write_config)
    @mock.patch('tap_deputy.utils.read_config')
    @mock.patch('tap_deputy.client.DeputyClient.post')
    def test_dev_mode_not_enabled_expired_token(self, mocked_request, mocked_read_config, mocked_write_config, mocked_json_dump):
        test_config["expires_at"] = strftime(now() - timedelta(days=1))
        write_new_config_file()
        deputy = DeputyClient(config=test_config, config_path=test_config_path, dev_mode=False)
        old_expiry_date = test_config["expires_at"]
        mocked_request.return_value = {
            "refresh_token": "new_refresh_token",
            "access_token": "new_access_token",
            "expires_in": 86400
        }
        deputy.refresh()
        
        self.assertEqual(mocked_read_config.call_count, 1)
        self.assertEqual(mocked_write_config.call_count, 1)
        self.assertEqual(deputy.refresh_token, "new_refresh_token")
        self.assertEqual(deputy.access_token, "new_access_token")
        self.assertGreater(deputy.expires_at, strptime_to_utc(old_expiry_date))
        tear_down()

    @mock.patch('tap_deputy.client.DeputyClient.post')
    def test_dev_mode_not_enabled_valid_token(self, mocked_request):
        """Verify that in dev mode token validation succeeds with token is not expired"""
        test_config["expires_at"] = strftime(now() + timedelta(days=1))
        old_expiry_date = test_config["expires_at"]
        write_new_config_file()
        deputy = DeputyClient(config=test_config, config_path=test_config_path, dev_mode=False)
        self.assertIsNone(deputy.refresh())
        self.assertEqual(deputy.refresh_token, "old_refresh_token")
        self.assertEqual(deputy.access_token, "old_access_token")
        self.assertEqual(deputy.expires_at, strptime_to_utc(old_expiry_date))
        tear_down()

    def test_dev_mode_enabled_valid_token(self):
        """Verify that in dev mode token validation succeeds with token is not expired"""
        test_config["expires_at"] = strftime(now() + timedelta(days=1))
        write_new_config_file()
        deputy = DeputyClient(config=test_config, config_path=test_config_path, dev_mode=True)
        self.assertIsNone(deputy.refresh())
        self.assertEqual(deputy.refresh_token, "old_refresh_token")
        self.assertEqual(deputy.access_token, "old_access_token")
        tear_down()

    def test_dev_mode_enabled_expired_token(self):
        """Verify that exception is raised when dev mode is enabled and token is expired"""
        test_config["expires_at"] = strftime(now() - timedelta(days=1))
        write_new_config_file()
        deputy = DeputyClient(config=test_config, config_path=test_config_path, dev_mode=True)
        try:
            deputy.refresh()
        except Exception as e:
            self.assertEqual(str(e), "Access Token in config is expired, unable to authenticate in dev mode")
        tear_down()
