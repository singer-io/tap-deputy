"""
Verifies that when only automatic fields are selected (primary key ``Id`` and
replication key ``Modified``), the tap still replicates records correctly.

Note on Deputy catalog inclusions
----------------------------------
tap-deputy marks only ``Id`` as ``inclusion: automatic`` in the catalog; all
other fields (including ``Modified``) are ``inclusion: available``.  At the
Singer spec level, however, the replication key must always be present in
records for bookmarking to work correctly.  This test therefore treats *both*
``Id`` and ``Modified`` as the minimum required field set, matching the
``expected_automatic_fields`` computed by BaseCase (PRIMARY_KEYS | REPLICATION_KEYS).
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
