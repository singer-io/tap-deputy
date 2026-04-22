"""
Verifies that when only automatic fields are selected (primary key ``Id`` and
replication key ``Modified``), the tap still replicates records correctly.

Note on Deputy catalog inclusions
----------------------------------
tap-deputy marks both ``Id`` and ``Modified`` as automatic/minimum required
fields for this test scenario. This matches the catalog metadata produced by
discovery and the ``expected_automatic_fields`` computed by BaseCase
(PRIMARY_KEYS | REPLICATION_KEYS).
"""
from tap_tester.base_suite_tests.automatic_fields_test import MinimumSelectionTest

from base import DeputyBase


class DeputyMinimumSelectionTest(MinimumSelectionTest, DeputyBase):
    """Test that the tap replicates records even with only automatic fields selected"""

    @staticmethod
    def name():
        return "tap_tester_deputy_combined_test"

    def streams_to_test(self):
        return {"system_usage_tracking", "system_usage_balances"}
