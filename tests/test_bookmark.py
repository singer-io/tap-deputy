"""
Verifies the tap resumes from its previous position rather than re-syncing
from the start, preventing duplicate records and unnecessary Deputy API usage.

Deputy-specific bookmark format
--------------------------------
Deputy stores bookmarks as a plain ISO-8601 string at the stream level::

    {"bookmarks": {"employees": "2024-01-15T08:30:00.000000Z"}}

rather than the Singer-standard nested format::

    {"bookmarks": {"employees": {"Modified": "2024-01-15T08:30:00.000000Z"}}}

``get_bookmark_value`` and ``manipulate_state`` are both overridden to handle
this flat structure so the base BookmarkTest assertions work correctly.
"""
import os
from copy import deepcopy

from tap_tester.base_suite_tests.bookmark_test import BookmarkTest

from base import DeputyBase


class DeputyBookmarkTest(BookmarkTest, DeputyBase):
    """A pre-seeded state must cause the second sync to skip already-seen records."""

    @staticmethod
    def name():
        return "tap_tester_deputy_bookmark_test"

    # -------------------------------------------------------------------
    # Bookmark wire format used by tap-deputy (plain ISO-8601 string)
    # -------------------------------------------------------------------
    # Deputy bookmarks are stored with local timezone offsets (e.g. -07:00)
    # but get_bookmark_value normalizes them to UTC via singer.utils.strftime,
    # which always produces the format: 2026-03-29T07:02:55.000000Z
    bookmark_format = "%Y-%m-%dT%H:%M:%S.%fZ"

    # Pre-seed state so that sync 1 only replays the most recent data,
    # keeping wall-clock time reasonable.  The date is intentionally set
    # close enough to now that the sync is fast, but far enough back that
    # both streams have at least some records after this point.
    # Format matches tap-deputy's start_date format (no microseconds, Z suffix)
    # which is what the Deputy QUERY API accepts.
    initial_bookmarks = {
        'bookmarks': {stream: '2025-01-01T00:00:00Z' for stream in ["system_usage_tracking", "system_usage_balances"]}
    }

    def streams_to_test(self):
        return {"system_usage_tracking", "system_usage_balances"}

    # -------------------------------------------------------------------
    # Deputy-specific overrides
    # -------------------------------------------------------------------

    @staticmethod
    def manipulate_state(state: dict, new_bookmarks: dict) -> dict:
        """
        Translate the standard ``{stream: {replication_key: value}}`` format
        produced by ``calculate_new_bookmarks`` into the flat deputy format
        ``{stream: value}`` expected by the tap's state reader.
        """
        new_state = deepcopy(state)
        if new_state.get('bookmarks') is None:
            new_state['bookmarks'] = {}
        for stream, rep in new_bookmarks.items():
            if isinstance(rep, dict):
                # Extract the single replication-key value ({"Modified": "…"})
                replication_value = next(iter(rep.values()))
            else:
                replication_value = rep
            new_state['bookmarks'][stream] = replication_value
        return new_state

    def get_bookmark_value(self, state: dict, stream: str):
        """
        Deputy stores bookmark state as a plain ISO-8601 string at the stream
        level rather than the Singer-standard nested format::

            # Deputy (flat)
            {"bookmarks": {"employees": "2024-01-15T08:30:00-07:00"}}

            # Standard Singer (nested)
            {"bookmarks": {"employees": {"Modified": "2024-01-15T08:30:00-07:00"}}}

        The base-class implementation calls ``.get(replication_key)`` on the
        stream bookmark, which would raise ``AttributeError`` on a plain string.
        This override reads the scalar value directly and normalizes it to UTC
        so the test's ``parse_date`` comparison is always between UTC datetimes
        (matching the transformed record values which Singer converts to UTC).
        """
        from singer.utils import strptime_to_utc, strftime
        replication_method = self.expected_replication_method(stream)
        if replication_method != self.INCREMENTAL:
            return None
        raw = state.get('bookmarks', {}).get(stream)
        if not raw:
            return None
        # Normalize to UTC Z-suffix so parse_date comparison works correctly.
        try:
            return strftime(strptime_to_utc(raw))
        except Exception:  # pylint: disable=broad-except
            return raw
