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

from base import DeputyBase, _DEV_WRAPPER_PATH


class DeputyBookmarkTest(BookmarkTest, DeputyBase):
    """A pre-seeded state must cause the second sync to skip already-seen records."""

    # -------------------------------------------------------------------
    # Bookmark wire format used by tap-deputy (plain ISO-8601 string)
    # -------------------------------------------------------------------
    # Deputy writes bookmarks as ISO-8601 with a UTC-offset, e.g.
    # "2026-03-27T00:02:56-07:00".  Python's %z directive handles ±HH:MM
    # offsets in 3.7+ so this matches the actual wire format exactly.
    bookmark_format = "%Y-%m-%dT%H:%M:%S%z"

    # Pre-seed state so that sync 1 only replays the most recent data,
    # keeping wall-clock time reasonable.  The date is intentionally set
    # close enough to now that the sync is fast, but far enough back that
    # both streams have at least some records after this point.
    # Format matches tap-deputy's start_date format (no microseconds, Z suffix)
    # which is what the Deputy QUERY API accepts.
    initial_bookmarks = {
        'bookmarks': {stream: '2025-01-01T00:00:00Z' for stream in ["system_usage_tracking", "system_usage_balances"]}
    }

    @staticmethod
    def name():
        return "tap_tester_deputy_bookmark_test"

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
        This override reads the scalar value directly.
        """
        replication_method = self.expected_replication_method(stream)
        if replication_method != self.INCREMENTAL:
            return None
        return state.get('bookmarks', {}).get(stream) or None

    def run_and_verify_sync_mode(self, conn_id):
        """
        Re-assert ``STITCH_TAP_PATH`` before every sync invocation.

        ``InMemoryBackend.run_sync_mode`` reads ``STITCH_TAP_PATH`` via
        ``os.getenv`` at call time, so both the first and second sync should
        pick it up correctly.  However, if the first sync subprocess runs
        without ``--dev`` for any reason (e.g. a transient env-var loss or
        a test-runner that resets the environment between calls), it triggers
        a real OAuth exchange that rotates the Deputy refresh token—leaving
        the second sync with an invalid token and no ``--dev`` protection.

        Re-pinning the path before every call guarantees dev mode is active
        for each sync, preventing the OAuth rotation side-effect.
        """
        os.environ['STITCH_TAP_PATH'] = _DEV_WRAPPER_PATH
        return super().run_and_verify_sync_mode(conn_id)
