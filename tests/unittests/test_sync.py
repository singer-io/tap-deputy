"""
Unit tests for tap_deputy.sync.

Covers:
- get_bookmark / write_bookmark state helpers
- write_schema Singer output call
- process_records: transform, write_record, max-Modified tracking
- sync_stream: QUERY params, pagination termination, bookmark-per-page
- update_current_stream: currently_syncing and write_state
- sync: catalog discovery fallback, stream iteration, end-state call
"""
import unittest
from unittest.mock import MagicMock, patch, call

import singer
from singer import metadata as singer_metadata

from tap_deputy.sync import (
    get_bookmark,
    write_bookmark,
    write_schema,
    process_records,
    sync_stream,
    update_current_stream,
    sync,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stream(stream_name="employees", key_properties=None):
    stream = MagicMock()
    stream.tap_stream_id = stream_name
    stream.key_properties = key_properties or ["Id"]
    stream.schema.to_dict.return_value = {
        "type": "object",
        "properties": {
            "Id": {"type": ["null", "integer"]},
            "Modified": {"type": ["null", "string"], "format": "date-time"},
            "Name": {"type": ["null", "string"]},
        },
    }
    return stream


def _make_mdata(resource_name="Employee"):
    # singer_metadata.new() returns the internal map format {breadcrumb: {...}}
    # singer_metadata.write() mutates and returns that same map — no to_map() needed
    mdata = singer_metadata.new()
    singer_metadata.write(mdata, (), "tap-deputy.resource", resource_name)
    return mdata


def _make_records(count, base_date="2024-01-01T00:00:00Z"):
    """Build a list of minimal employee records with valid, sequential Modified timestamps."""
    from datetime import datetime, timedelta, timezone
    base = datetime.strptime(base_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return [
        {
            "Id": i,
            "Modified": (base + timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Name": f"Person {i}",
        }
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# get_bookmark
# ---------------------------------------------------------------------------

class TestGetBookmark(unittest.TestCase):

    def test_returns_default_when_no_bookmarks_key(self):
        """get_bookmark returns default when state has no 'bookmarks'."""
        self.assertEqual(
            get_bookmark({}, "employees", "2020-01-01T00:00:00Z"),
            "2020-01-01T00:00:00Z",
        )

    def test_returns_default_when_stream_not_in_bookmarks(self):
        """get_bookmark returns default when stream is absent from bookmarks."""
        state = {"bookmarks": {"other_stream": "2023-01-01T00:00:00Z"}}
        self.assertEqual(
            get_bookmark(state, "employees", "2020-01-01T00:00:00Z"),
            "2020-01-01T00:00:00Z",
        )

    def test_returns_stored_bookmark(self):
        """get_bookmark returns the value stored for the stream."""
        state = {"bookmarks": {"employees": "2024-06-01T00:00:00Z"}}
        self.assertEqual(
            get_bookmark(state, "employees", "2020-01-01T00:00:00Z"),
            "2024-06-01T00:00:00Z",
        )


# ---------------------------------------------------------------------------
# write_bookmark
# ---------------------------------------------------------------------------

class TestWriteBookmark(unittest.TestCase):

    @patch("tap_deputy.sync.singer.write_state")
    def test_creates_bookmarks_dict_when_missing(self, mock_ws):
        """write_bookmark creates the 'bookmarks' key when absent."""
        state = {}
        write_bookmark(state, "employees", "2024-01-01T00:00:00Z")
        self.assertIn("bookmarks", state)
        self.assertEqual(state["bookmarks"]["employees"], "2024-01-01T00:00:00Z")

    @patch("tap_deputy.sync.singer.write_state")
    def test_writes_value_to_state(self, mock_ws):
        """write_bookmark stores the value under the stream name."""
        state = {"bookmarks": {}}
        write_bookmark(state, "employees", "2024-06-15T00:00:00Z")
        self.assertEqual(state["bookmarks"]["employees"], "2024-06-15T00:00:00Z")

    @patch("tap_deputy.sync.singer.write_state")
    def test_calls_singer_write_state(self, mock_ws):
        """write_bookmark calls singer.write_state with the updated state."""
        state = {}
        write_bookmark(state, "employees", "2024-01-01T00:00:00Z")
        mock_ws.assert_called_once_with(state)


# ---------------------------------------------------------------------------
# write_schema
# ---------------------------------------------------------------------------

class TestWriteSchema(unittest.TestCase):

    @patch("tap_deputy.sync.singer.write_schema")
    def test_calls_singer_write_schema(self, mock_ws):
        """write_schema calls singer.write_schema with stream id, schema, key_props."""
        stream = _make_stream("employees")
        write_schema(stream)
        mock_ws.assert_called_once_with(
            "employees",
            stream.schema.to_dict(),
            stream.key_properties,
        )


# ---------------------------------------------------------------------------
# process_records
# ---------------------------------------------------------------------------

class TestProcessRecords(unittest.TestCase):

    @patch("tap_deputy.sync.singer.write_record")
    def test_writes_each_record(self, mock_wr):
        """process_records calls singer.write_record once per record."""
        records = _make_records(3)
        stream = _make_stream()
        mdata = _make_mdata()
        process_records(stream, mdata, "2020-01-01T00:00:00Z", records)
        self.assertEqual(mock_wr.call_count, 3)

    @patch("tap_deputy.sync.singer.write_record")
    def test_returns_max_modified(self, mock_wr):
        """process_records returns the highest Modified value seen."""
        records = _make_records(3)
        stream = _make_stream()
        mdata = _make_mdata()
        result = process_records(stream, mdata, "2020-01-01T00:00:00Z", records)
        # records have Modified: T00:00:00Z, T00:00:01Z, T00:00:02Z
        self.assertEqual(result, "2024-01-01T00:00:02Z")

    @patch("tap_deputy.sync.singer.write_record")
    def test_returns_initial_max_when_empty_records(self, mock_wr):
        """process_records returns the incoming max_modified when given no records."""
        stream = _make_stream()
        mdata = _make_mdata()
        result = process_records(stream, mdata, "2023-05-01T00:00:00Z", [])
        self.assertEqual(result, "2023-05-01T00:00:00Z")
        mock_wr.assert_not_called()

    @patch("tap_deputy.sync.singer.write_record")
    def test_does_not_decrease_max_modified(self, mock_wr):
        """process_records never lowers max_modified below the incoming value."""
        stream = _make_stream()
        mdata = _make_mdata()
        # Record has an older Modified than the incoming max
        records = [{"Id": 1, "Modified": "2022-01-01T00:00:00Z", "Name": "Old"}]
        result = process_records(stream, mdata, "2024-01-01T00:00:00Z", records)
        self.assertEqual(result, "2024-01-01T00:00:00Z")


# ---------------------------------------------------------------------------
# sync_stream
# ---------------------------------------------------------------------------

class TestSyncStream(unittest.TestCase):

    def _run_sync_stream(self, pages, start_date="2020-01-01T00:00:00Z", state=None):
        """
        Run sync_stream with a mocked client that returns `pages` in order.
        pages: list of record lists; pagination stops when len(page) < 500.
        """
        client = MagicMock()
        client.post.side_effect = pages

        stream = _make_stream("employees")
        mdata = _make_mdata("Employee")
        if state is None:
            state = {}

        with patch("tap_deputy.sync.singer.write_schema"), \
             patch("tap_deputy.sync.singer.write_record"), \
             patch("tap_deputy.sync.singer.write_state"):
            sync_stream(client, MagicMock(), state, start_date, stream, mdata)

        return client

    def test_uses_start_date_when_no_bookmark(self):
        """sync_stream sends the start_date as the QUERY data when no bookmark."""
        client = self._run_sync_stream(
            pages=[[]],
            start_date="2022-01-01T00:00:00Z",
        )
        query = client.post.call_args[1]["json"]
        self.assertEqual(query["search"]["s1"]["data"], "2022-01-01T00:00:00Z")

    def test_uses_bookmark_when_present(self):
        """sync_stream sends the stored bookmark as QUERY data."""
        state = {"bookmarks": {"employees": "2024-03-01T00:00:00Z"}}
        client = self._run_sync_stream(pages=[[]], state=state)
        query = client.post.call_args[1]["json"]
        self.assertEqual(query["search"]["s1"]["data"], "2024-03-01T00:00:00Z")

    def test_query_filters_on_modified_gte(self):
        """QUERY params request Modified >= bookmark with ascending sort."""
        client = self._run_sync_stream(pages=[[]])
        query = client.post.call_args[1]["json"]
        self.assertEqual(query["search"]["s1"]["field"], "Modified")
        self.assertEqual(query["search"]["s1"]["type"], "ge")
        self.assertEqual(query["sort"]["Modified"], "asc")

    def test_single_page_terminates_when_fewer_than_count(self):
        """Pagination stops when the returned page is smaller than count (500)."""
        records = _make_records(10)
        client = self._run_sync_stream(pages=[records])
        self.assertEqual(client.post.call_count, 1)

    def test_multiple_pages_until_partial_page(self):
        """Pagination continues over full pages and stops on a partial page."""
        full_page = _make_records(500)
        partial_page = _make_records(20)
        client = self._run_sync_stream(pages=[full_page, partial_page])
        self.assertEqual(client.post.call_count, 2)

    @patch("tap_deputy.sync.singer.write_schema")
    @patch("tap_deputy.sync.singer.write_record")
    @patch("tap_deputy.sync.singer.write_state")
    def test_bookmark_written_after_each_page(self, mock_ws, mock_wr, mock_wsc):
        """write_bookmark (which calls singer.write_state) is called after every page."""
        full_page = _make_records(500)
        partial_page = _make_records(5)
        client = MagicMock()
        client.post.side_effect = [full_page, partial_page]
        stream = _make_stream("employees")
        mdata = _make_mdata("Employee")
        state = {}

        sync_stream(client, MagicMock(), state, "2020-01-01T00:00:00Z", stream, mdata)

        # write_state called twice: once per page (via write_bookmark)
        self.assertEqual(mock_ws.call_count, 2)

    def test_posts_to_correct_resource_endpoint(self):
        """sync_stream POSTs to /api/v1/resource/<resource>/QUERY."""
        client = self._run_sync_stream(pages=[[]])
        called_path = client.post.call_args[0][0]
        self.assertIn("Employee", called_path)
        self.assertIn("QUERY", called_path)


# ---------------------------------------------------------------------------
# update_current_stream
# ---------------------------------------------------------------------------

class TestUpdateCurrentStream(unittest.TestCase):

    @patch("tap_deputy.sync.singer.write_state")
    @patch("tap_deputy.sync.set_currently_syncing")
    def test_sets_currently_syncing(self, mock_scs, mock_ws):
        """update_current_stream calls set_currently_syncing with the stream name."""
        state = {}
        update_current_stream(state, "employees")
        mock_scs.assert_called_once_with(state, "employees")

    @patch("tap_deputy.sync.singer.write_state")
    @patch("tap_deputy.sync.set_currently_syncing")
    def test_calls_write_state(self, mock_scs, mock_ws):
        """update_current_stream calls singer.write_state after setting syncing."""
        state = {}
        update_current_stream(state, "employees")
        mock_ws.assert_called_once_with(state)

    @patch("tap_deputy.sync.singer.write_state")
    @patch("tap_deputy.sync.set_currently_syncing")
    def test_clears_currently_syncing_with_none(self, mock_scs, mock_ws):
        """update_current_stream passes None to clear the currently_syncing field."""
        state = {}
        update_current_stream(state)
        mock_scs.assert_called_once_with(state, None)


# ---------------------------------------------------------------------------
# sync (top-level entry point)
# ---------------------------------------------------------------------------

class TestSync(unittest.TestCase):

    def _make_catalog_stream(self, stream_name):
        stream = MagicMock()
        stream.tap_stream_id = stream_name
        stream.key_properties = ["Id"]
        stream.schema.to_dict.return_value = {
            "type": "object",
            "properties": {
                "Id": {"type": ["null", "integer"]},
                "Modified": {"type": ["null", "string"], "format": "date-time"},
            },
        }
        # Build the list-of-dicts format expected by metadata.to_map() in sync.py
        stream.metadata = [
            {
                "breadcrumb": [],
                "metadata": {"tap-deputy.resource": "Employee"},
            }
        ]
        return stream

    @patch("tap_deputy.sync.sync_stream")
    @patch("tap_deputy.sync.update_current_stream")
    def test_uses_catalog_selected_streams(self, mock_ucs, mock_ss):
        """sync() calls sync_stream for each selected stream in the catalog."""
        catalog = MagicMock()
        stream = self._make_catalog_stream("employees")
        catalog.get_selected_streams.return_value = [stream]
        client = MagicMock()

        sync(client, catalog, {}, "2020-01-01T00:00:00Z")

        mock_ss.assert_called_once()

    @patch("tap_deputy.sync.sync_stream")
    @patch("tap_deputy.sync.update_current_stream")
    @patch("tap_deputy.sync.discover")
    def test_runs_discover_when_no_catalog(self, mock_discover, mock_ucs, mock_ss):
        """sync() calls discover() when no catalog argument is provided."""
        stream = self._make_catalog_stream("employees")
        mock_catalog = MagicMock()
        mock_catalog.streams = [stream]
        mock_discover.return_value = mock_catalog
        client = MagicMock()

        sync(client, None, {}, "2020-01-01T00:00:00Z")

        mock_discover.assert_called_once_with(client)

    @patch("tap_deputy.sync.sync_stream")
    @patch("tap_deputy.sync.update_current_stream")
    def test_clears_currently_syncing_at_end(self, mock_ucs, mock_ss):
        """sync() calls update_current_stream(state) with no stream name at the end."""
        catalog = MagicMock()
        catalog.get_selected_streams.return_value = []
        client = MagicMock()
        state = {}

        sync(client, catalog, state, "2020-01-01T00:00:00Z")

        # Final call should be with state only (no stream name → None)
        last_call_args = mock_ucs.call_args_list[-1]
        self.assertEqual(last_call_args, call(state))

    @patch("tap_deputy.sync.sync_stream")
    @patch("tap_deputy.sync.update_current_stream")
    def test_sets_currently_syncing_before_each_stream(self, mock_ucs, mock_ss):
        """sync() calls update_current_stream with the stream name before syncing it."""
        catalog = MagicMock()
        stream = self._make_catalog_stream("employees")
        catalog.get_selected_streams.return_value = [stream]
        client = MagicMock()
        state = {}

        sync(client, catalog, state, "2020-01-01T00:00:00Z")

        first_call_args = mock_ucs.call_args_list[0]
        self.assertEqual(first_call_args, call(state, "employees"))


# ---------------------------------------------------------------------------
# utils helpers (tested indirectly where not covered by client tests)
# ---------------------------------------------------------------------------

class TestUtils(unittest.TestCase):

    def test_read_config_raises_on_missing_file(self):
        """read_config raises Exception for a non-existent path."""
        import os
        import tempfile
        import uuid
        from tap_deputy.utils import read_config

        missing_path = os.path.join(
            tempfile.gettempdir(),
            f"definitely_does_not_exist_deputy_{uuid.uuid4().hex}.json",
        )
        self.assertFalse(os.path.exists(missing_path))

        with self.assertRaises(Exception) as ctx:
            read_config(missing_path)
        self.assertIn("Failed to load config", str(ctx.exception))

    def test_write_config_merges_and_persists(self):
        """write_config merges new data into the existing config file."""
        import json, os, tempfile
        from tap_deputy.utils import write_config

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"existing_key": "existing_val"}, f)
            tmp_path = f.name

        try:
            result = write_config(tmp_path, {"new_key": "new_val"})
            self.assertEqual(result["existing_key"], "existing_val")
            self.assertEqual(result["new_key"], "new_val")
            with open(tmp_path) as f:
                on_disk = json.load(f)
            self.assertEqual(on_disk["new_key"], "new_val")
        finally:
            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
