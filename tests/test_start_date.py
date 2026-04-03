"""
Confirms the tap does not ignore start_date and re-replicate the full history
on every run, which would inflate API costs and flood downstream tables with
duplicates.

Deputy applies a ``Modified >= start_date`` filter in the QUERY endpoint, so
a later start date should produce a strict subset of the records returned by an
earlier start date (provided data exists between the two start dates).

start_date_1 is set far enough before start_date_2 to ensure that the test
account has records in the gap between the two dates for the most common streams.
"""
from tap_tester.base_suite_tests.start_date_test import StartDateTest

from base import DeputyBase


class DeputyStartDateTest(StartDateTest, DeputyBase):
    """A later start_date must yield a strict subset of the records from an earlier one."""

    def streams_to_test(self):
        return {"system_usage_tracking", "system_usage_balances"}

    @property
    def start_date_1(self):
        return '2022-01-01T00:00:00Z'

    @property
    def start_date_2(self):
        return '2025-01-01T00:00:00Z'
