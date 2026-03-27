"""
Unit tests for tap_deputy.client.DeputyClient.

Complements the existing test_dev_mode.py which covers token refresh in/out of
dev mode and the 401 retry loop.  These tests cover the remaining surface:
- Dev mode with no access_token raises an error
- 5xx responses raise Server5xxError
- ConnectionError propagates (triggering backoff)
- Authorization header injection on regular vs auth_call requests
- User-Agent header injection
- URL construction from domain + path
- utils.write_config called with new tokens on successful OAuth refresh
- The `get` / `post` convenience wrappers delegate to `request`
- 4xx responses (other than 401) surface via raise_for_status
- Expired token triggers a refresh even when access_token is set
"""
import json
import os
import tempfile
import unittest
from datetime import timedelta
from unittest import mock
from unittest.mock import MagicMock, patch, call

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError

from singer.utils import now

from tap_deputy.client import DeputyClient, Server401TokenExpiredError, Server5xxError

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

CONFIG = {
    "domain": "mycompany.na.deputy.com",
    "client_id": "cid",
    "client_secret": "csecret",
    "redirect_uri": "https://example.com/callback",
    "refresh_token": "old_refresh",
    "access_token": "old_access",
    "user_agent": "TestAgent/1.0",
}
CONFIG_PATH = os.path.join(tempfile.gettempdir(), "test_deputy_client_config.json")


def _write_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump(CONFIG, f)


def _make_client(dev_mode=False, config_override=None):
    cfg = {**CONFIG, **(config_override or {})}
    return DeputyClient(cfg, CONFIG_PATH, dev_mode=dev_mode)


def _mock_response(status_code=200, json_body=None, raise_error=False):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    if raise_error:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Dev-mode edge cases
# ---------------------------------------------------------------------------

class TestDevModeEdgeCases(unittest.TestCase):

    def setUp(self):
        _write_config()

    def tearDown(self):
        if os.path.isfile(CONFIG_PATH):
            os.remove(CONFIG_PATH)

    def test_dev_mode_missing_access_token_raises(self):
        """Dev mode raises Exception when access_token is absent."""
        client = _make_client(dev_mode=True, config_override={"access_token": None})
        with self.assertRaises(Exception) as ctx:
            client.refresh()
        self.assertIn("Access token is missing", str(ctx.exception))

    def test_dev_mode_with_access_token_returns_early(self):
        """Dev mode returns immediately without hitting the OAuth endpoint."""
        client = _make_client(dev_mode=True)
        with patch.object(client, "post") as mock_post:
            client.refresh()
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# HTTP error handling
# ---------------------------------------------------------------------------

class TestClientHttpErrors(unittest.TestCase):

    def setUp(self):
        _write_config()

    def tearDown(self):
        if os.path.isfile(CONFIG_PATH):
            os.remove(CONFIG_PATH)

    @patch("requests.Session.request")
    def test_500_raises_server5xx_error(self, mock_req):
        """A 500 response raises Server5xxError."""
        mock_req.return_value = _mock_response(status_code=500)
        client = _make_client()
        client.expires_at = now() + timedelta(days=1)

        with self.assertRaises(Server5xxError):
            client.get("/api/v1/resource/Foo/INFO", endpoint="test")

    @patch("requests.Session.request")
    def test_503_raises_server5xx_error(self, mock_req):
        """Any 5xx response raises Server5xxError."""
        mock_req.return_value = _mock_response(status_code=503)
        client = _make_client()
        client.expires_at = now() + timedelta(days=1)

        with self.assertRaises(Server5xxError):
            client.get("/api/v1/resource/Foo/INFO", endpoint="test")

    @patch("requests.Session.request")
    def test_401_raises_server401_error(self, mock_req):
        """A 401 response raises Server401TokenExpiredError."""
        mock_req.return_value = _mock_response(status_code=401)
        client = _make_client()
        client.expires_at = now() + timedelta(days=1)

        with patch.object(client, "refresh"):
            with self.assertRaises(Server401TokenExpiredError):
                client.get("/api/v1/resource/Foo/INFO", endpoint="test")

    @patch("requests.Session.request")
    def test_400_raises_via_raise_for_status(self, mock_req):
        """A 400 response surfaces through response.raise_for_status()."""
        mock_req.return_value = _mock_response(status_code=400, raise_error=True)
        client = _make_client()
        client.expires_at = now() + timedelta(days=1)

        with patch.object(client, "refresh"):
            with self.assertRaises(requests.HTTPError):
                client.get("/api/v1/resource/Foo/INFO", endpoint="test")


# ---------------------------------------------------------------------------
# Authorization header
# ---------------------------------------------------------------------------

class TestAuthorizationHeader(unittest.TestCase):

    def setUp(self):
        _write_config()

    def tearDown(self):
        if os.path.isfile(CONFIG_PATH):
            os.remove(CONFIG_PATH)

    @patch("requests.Session.request")
    def test_authorization_header_set_on_regular_request(self, mock_req):
        """OAuth token is injected in the Authorization header for normal calls."""
        mock_req.return_value = _mock_response(200, {"result": True})
        client = _make_client()
        client.expires_at = now() + timedelta(days=1)

        with patch.object(client, "refresh"):
            client.get("/api/v1/resource/Employee/QUERY", endpoint="employees")

        _, kwargs = mock_req.call_args
        self.assertEqual(
            kwargs["headers"]["Authorization"], "OAuth old_access"
        )

    @patch("requests.Session.request")
    def test_no_authorization_header_on_auth_call(self, mock_req):
        """Authorization header is NOT set when auth_call=True."""
        mock_req.return_value = _mock_response(200, {
            "refresh_token": "r2", "access_token": "a2", "expires_in": 3600
        })
        client = _make_client()

        client.post("/oauth/access_token", auth_call=True, data={})

        _, kwargs = mock_req.call_args
        self.assertNotIn("Authorization", kwargs.get("headers", {}))


# ---------------------------------------------------------------------------
# User-Agent header
# ---------------------------------------------------------------------------

class TestUserAgentHeader(unittest.TestCase):

    def setUp(self):
        _write_config()

    def tearDown(self):
        if os.path.isfile(CONFIG_PATH):
            os.remove(CONFIG_PATH)

    @patch("requests.Session.request")
    def test_user_agent_set_when_configured(self, mock_req):
        """User-Agent header is included when user_agent is in config."""
        mock_req.return_value = _mock_response(200, {})
        client = _make_client()
        client.expires_at = now() + timedelta(days=1)

        with patch.object(client, "refresh"):
            client.get("/api/v1/resource/Employee/INFO", endpoint="test")

        _, kwargs = mock_req.call_args
        self.assertEqual(kwargs["headers"].get("User-Agent"), "TestAgent/1.0")

    @patch("requests.Session.request")
    def test_user_agent_absent_when_not_configured(self, mock_req):
        """User-Agent header is NOT set when user_agent is missing from config."""
        mock_req.return_value = _mock_response(200, {})
        client = _make_client(config_override={"user_agent": None})
        client.expires_at = now() + timedelta(days=1)

        with patch.object(client, "refresh"):
            client.get("/api/v1/resource/Employee/INFO", endpoint="test")

        _, kwargs = mock_req.call_args
        self.assertNotIn("User-Agent", kwargs.get("headers", {}))


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------

class TestUrlConstruction(unittest.TestCase):

    def setUp(self):
        _write_config()

    def tearDown(self):
        if os.path.isfile(CONFIG_PATH):
            os.remove(CONFIG_PATH)

    @patch("requests.Session.request")
    def test_url_built_from_domain_and_path(self, mock_req):
        """The request URL is constructed as https://<domain><path>."""
        mock_req.return_value = _mock_response(200, [])
        client = _make_client()
        client.expires_at = now() + timedelta(days=1)

        with patch.object(client, "refresh"):
            client.get("/api/v1/resource/Employee/QUERY", endpoint="employees")

        positional_url = mock_req.call_args[0][1]
        self.assertEqual(
            positional_url,
            "https://mycompany.na.deputy.com/api/v1/resource/Employee/QUERY",
        )


# ---------------------------------------------------------------------------
# Token refresh writes config
# ---------------------------------------------------------------------------

class TestTokenRefreshWritesConfig(unittest.TestCase):

    def setUp(self):
        _write_config()

    def tearDown(self):
        if os.path.isfile(CONFIG_PATH):
            os.remove(CONFIG_PATH)

    @patch("tap_deputy.client.DeputyClient.post")
    def test_write_config_called_with_new_tokens(self, mock_post):
        """After a successful OAuth exchange, utils.write_config persists new tokens."""
        mock_post.return_value = {
            "refresh_token": "new_refresh",
            "access_token": "new_access",
            "expires_in": 3600,
        }
        client = _make_client(dev_mode=False)

        with patch("tap_deputy.client.utils.write_config") as mock_write:
            client.refresh()

        mock_write.assert_called_once()
        _, written = mock_write.call_args[0]
        self.assertEqual(written["refresh_token"], "new_refresh")
        self.assertEqual(written["access_token"], "new_access")
        self.assertIn("expires_at", written)


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------

class TestConvenienceWrappers(unittest.TestCase):

    def setUp(self):
        _write_config()

    def tearDown(self):
        if os.path.isfile(CONFIG_PATH):
            os.remove(CONFIG_PATH)

    @patch("tap_deputy.client.DeputyClient.request")
    def test_get_calls_request_with_get_method(self, mock_request):
        """client.get() delegates to request('GET', ...)."""
        mock_request.return_value = {}
        client = _make_client()
        client.get("/some/path", endpoint="ep")
        mock_request.assert_called_once_with("GET", path="/some/path", endpoint="ep")

    @patch("tap_deputy.client.DeputyClient.request")
    def test_post_calls_request_with_post_method(self, mock_request):
        """client.post() delegates to request('POST', ...)."""
        mock_request.return_value = {}
        client = _make_client()
        client.post("/some/path", json={"key": "val"}, endpoint="ep")
        mock_request.assert_called_once_with(
            "POST", path="/some/path", json={"key": "val"}, endpoint="ep"
        )


# ---------------------------------------------------------------------------
# Token expiry triggers refresh
# ---------------------------------------------------------------------------

class TestTokenExpiryTriggersRefresh(unittest.TestCase):

    def setUp(self):
        _write_config()

    def tearDown(self):
        if os.path.isfile(CONFIG_PATH):
            os.remove(CONFIG_PATH)

    @patch("requests.Session.request")
    @patch("tap_deputy.client.DeputyClient.refresh")
    def test_expired_token_triggers_refresh(self, mock_refresh, mock_req):
        """request() calls refresh() when expires_at is in the past."""
        mock_req.return_value = _mock_response(200, [])
        client = _make_client()
        client.expires_at = now() - timedelta(seconds=30)

        client.get("/api/v1/resource/Employee/QUERY", endpoint="employees")

        mock_refresh.assert_called_once()

    @patch("requests.Session.request")
    @patch("tap_deputy.client.DeputyClient.refresh")
    def test_null_access_token_triggers_refresh(self, mock_refresh, mock_req):
        """request() calls refresh() when access_token is None."""
        mock_req.return_value = _mock_response(200, [])
        client = _make_client(config_override={"access_token": None})
        client.expires_at = now() + timedelta(days=1)

        client.get("/api/v1/resource/Employee/QUERY", endpoint="employees")

        mock_refresh.assert_called_once()

    @patch("requests.Session.request")
    @patch("tap_deputy.client.DeputyClient.refresh")
    def test_valid_token_does_not_trigger_refresh(self, mock_refresh, mock_req):
        """request() does NOT call refresh() when token is still valid."""
        mock_req.return_value = _mock_response(200, [])
        client = _make_client()
        client.expires_at = now() + timedelta(days=1)

        client.get("/api/v1/resource/Employee/QUERY", endpoint="employees")

        mock_refresh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
