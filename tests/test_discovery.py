"""
Validates that catalog entries produced by discovery match the expected schema,
replication method, and key metadata so downstream consumers can rely on them
without inspecting the tap source.

Deputy discovery hits the /api/v1/resource/<Resource>/INFO endpoint for each
of the 60 supported resources and derives field types from the Deputy type map.
Json-typed fields are intentionally skipped.
"""
from tap_tester.base_suite_tests.discovery_test import DiscoveryTest

from base import DeputyBase


class DeputyDiscoveryTest(DiscoveryTest, DeputyBase):
    """Standard Discovery Test"""

    @staticmethod
    def name():
        return "tap_tester_deputy_discovery_test"

    def streams_to_test(self):
        return self.expected_stream_names()
