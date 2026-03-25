"""
Validates that catalog entries produced by discovery match the expected schema,
replication method, and key metadata so downstream consumers can rely on them
without inspecting the tap source.

Deputy discovery hits the /api/v1/resource/<Resource>/INFO endpoint for each
of the 60 supported resources and derives field types from the Deputy type map.
Json-typed fields are intentionally skipped.
"""
from tap_tester.base_suite_tests.discovery_test import DiscoveryTest
from tap_tester import connections

from base import DeputyBase


class DeputyDiscoveryTest(DiscoveryTest, DeputyBase):
    """Standard Discovery Test"""

    # Class-level cache scoped to this class, independent of the shared
    # DiscoveryTest.conn_id / DiscoveryTest.found_catalogs which may be
    # populated by another tap's discovery test running in the same session.
    _deputy_conn_id = None
    _deputy_found_catalogs = None

    @staticmethod
    def name():
        return "tap_tester_deputy_discovery_test"

    def streams_to_test(self):
        return self.expected_stream_names()

    def setUp(self):  # pylint: disable=invalid-name
        """
        Override setUp to use Deputy-scoped class variables so that a stale
        DiscoveryTest.conn_id (set by another tap's test in the same session)
        does not bypass initialization and leave found_catalogs as None.
        """
        # Run BaseCase.setUp hooks but skip DiscoveryTest.setUp so we own caching.
        DeputyBase.setUp(self, logging="Run setup for DeputyDiscoveryTest")

        if DeputyDiscoveryTest._deputy_found_catalogs is None:
            if DeputyDiscoveryTest._deputy_conn_id is None:
                DeputyDiscoveryTest._deputy_conn_id = connections.ensure_connection(self)
            DeputyDiscoveryTest._deputy_found_catalogs = \
                self.run_and_verify_check_mode(DeputyDiscoveryTest._deputy_conn_id)

        # Always push Deputy-scoped values into DiscoveryTest so inherited
        # test methods (test_replication_metadata, test_unsupported_fields, …)
        # always see the correct Deputy catalog regardless of session order.
        DiscoveryTest.conn_id = DeputyDiscoveryTest._deputy_conn_id
        DiscoveryTest.found_catalogs = DeputyDiscoveryTest._deputy_found_catalogs
