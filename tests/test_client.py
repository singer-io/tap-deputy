"""
DeputyTestClient — mirrors tap-adroll's TestClient pattern.

Fetches a *fresh* Deputy OAuth access_token at test-class setup time using the
refresh_token grant.  This removes the need for a static TAP_DEPUTY_ACCESS_TOKEN
environment variable that would expire after 24 h.

Required environment variables
-------------------------------
TAP_DEPUTY_DOMAIN        – e.g. 4438cb05110151.na.deputy.com
TAP_DEPUTY_CLIENT_ID     – OAuth application client_id
TAP_DEPUTY_CLIENT_SECRET – OAuth application client_secret
TAP_DEPUTY_REDIRECT_URI  – registered redirect URI
TAP_DEPUTY_REFRESH_TOKEN – long-lived refresh token
"""

import os

import requests


class DeputyTestClient:
    """Thin helper that exchanges a refresh_token for a fresh access_token."""

    @staticmethod
    def get_token_information() -> dict:
        """Return a dict with fresh ``access_token``, ``refresh_token``, and
        the OAuth config fields required by get_credentials().

        Raises
        ------
        ValueError
            If any required environment variable is missing.
        RuntimeError
            If the Deputy OAuth endpoint returns a non-2xx response.
        """
        required = {
            'TAP_DEPUTY_DOMAIN': os.getenv('TAP_DEPUTY_DOMAIN'),
            'TAP_DEPUTY_CLIENT_ID': os.getenv('TAP_DEPUTY_CLIENT_ID'),
            'TAP_DEPUTY_CLIENT_SECRET': os.getenv('TAP_DEPUTY_CLIENT_SECRET'),
            'TAP_DEPUTY_REDIRECT_URI': os.getenv('TAP_DEPUTY_REDIRECT_URI'),
            'TAP_DEPUTY_REFRESH_TOKEN': os.getenv('TAP_DEPUTY_REFRESH_TOKEN'),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing environment variables: {missing}")

        domain = required['TAP_DEPUTY_DOMAIN']
        client_id = required['TAP_DEPUTY_CLIENT_ID']
        client_secret = required['TAP_DEPUTY_CLIENT_SECRET']
        redirect_uri = required['TAP_DEPUTY_REDIRECT_URI']
        refresh_token = required['TAP_DEPUTY_REFRESH_TOKEN']

        # If a ready-to-use access token is already in the environment (e.g.
        # obtained manually or via a prior refresh), use it directly and skip
        # the OAuth round-trip.  This avoids invalidating the refresh token
        # on accounts where only one outstanding access token is permitted.
        access_token = os.getenv('TAP_DEPUTY_ACCESS_TOKEN')
        if access_token:
            return {
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'access_token': access_token,
                'refresh_token': refresh_token,
            }

        response = requests.post(
            f"https://{domain}/oauth/access_token",
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'scope': 'longlife_refresh_token',
            },
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                f"Deputy token refresh failed [{response.status_code}]: {response.text}"
            )

        token = response.json()
        return {
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token'],
        }
