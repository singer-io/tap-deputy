"""
Catches field-level omissions: if the tap silently drops a field during sync,
consumers lose data with no visible error until they notice missing columns.

Deputy discovery derives its schema from the Deputy INFO endpoint at runtime,
so this test also acts as a regression guard against upstream schema changes.

Json-typed fields are excluded from discovery (see tap_deputy/discover.py) and
therefore absent from the catalog and this test.
"""
from tap_tester.base_suite_tests.all_fields_test import AllFieldsTest

from base import DeputyBase


class DeputyAllFieldsTest(AllFieldsTest, DeputyBase):
    """Test that with all fields selected, all fields are replicated"""

    @staticmethod
    def name():
        return "tap_tester_deputy_all_fields_test"

    def streams_to_test(self):
        return {"system_usage_tracking", "system_usage_balances"}