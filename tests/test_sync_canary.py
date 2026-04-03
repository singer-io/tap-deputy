"""
Smoke-test: confirms end-to-end connectivity between tap-deputy and the target.

The tap must produce at least one record across the expected streams, proving
that the OAuth token is valid, the Deputy subdomain is reachable, and the
QUERY endpoint is returning data.

A recent start_date is used to keep sync time short; set it far enough back
that at least one resource (e.g. employees) has a record in the test account.
"""
from tap_tester.base_suite_tests.sync_canary_test import SyncCanaryTest

from base import DeputyBase


class DeputySyncCanaryTest(SyncCanaryTest, DeputyBase):
    """The tap must produce at least one record to confirm end-to-end connectivity."""

    def streams_to_test(self):
        return {"system_usage_tracking", "system_usage_balances"}

    def setUp(self):  # pylint: disable=invalid-name
        # Use a recent window to keep the canary fast; adjust if the test
        # account does not have data within this range.
        self.start_date = '2025-01-01T00:00:00Z'
        super().setUp()
