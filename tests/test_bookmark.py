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
from copy import deepcopy

from tap_tester.base_suite_tests.bookmark_test import BookmarkTest

from base import DeputyBase, ALL_STREAM_NAMES


class DeputyBookmarkTest(BookmarkTest, DeputyBase):
    """A pre-seeded state must cause the second sync to skip already-seen records."""

    # -------------------------------------------------------------------
    # Bookmark wire format used by tap-deputy (plain ISO-8601 string)
    # -------------------------------------------------------------------
    bookmark_format = "%Y-%m-%dT%H:%M:%S.%fZ"

    # Pre-seed state so that sync 1 only replays the most recent data,
    # keeping wall-clock time reasonable.  The date is intentionally set
    # a few years back to ensure every stream that exists in the test
    # environment has data after this point.
    initial_bookmarks = {
        'bookmarks': {stream: '2023-01-01T00:00:00.000000Z' for stream in ALL_STREAM_NAMES}
    }

    @staticmethod
    def name():
        return "tap_tester_deputy_bookmark_test"

    def streams_to_test(self):
        return self.expected_stream_names()

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
