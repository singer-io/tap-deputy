"""
Unit tests for tap_deputy.discover.

Tests get_schema() field-type mapping, metadata generation, and the discover()
function that builds the Singer Catalog from RESOURCES.
No real HTTP calls are made — client.get() is mocked throughout.
"""
import unittest
from unittest.mock import MagicMock, patch

from singer.catalog import Catalog

from tap_deputy.discover import RESOURCES, TYPE_MAP, get_schema, discover


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(info_response=None):
    """Return a mock DeputyClient whose .get() returns info_response."""
    client = MagicMock()
    client.get.return_value = info_response or {"fields": {}}
    return client


def _info(fields: dict):
    """Build the data structure returned by the Deputy /INFO endpoint."""
    return {"fields": fields}


# ---------------------------------------------------------------------------
# get_schema – field-type mapping
# ---------------------------------------------------------------------------

class TestGetSchemaTypeMapping(unittest.TestCase):

    def test_integer_field_maps_to_integer_type(self):
        """Integer Deputy fields map to JSON Schema 'integer'."""
        client = _make_client(_info({"MyInt": "Integer"}))
        schema, _ = get_schema(client, "Employee")
        self.assertEqual(schema["properties"]["MyInt"], {"type": ["null", "integer"]})

    def test_float_field_maps_to_number_type(self):
        """Float Deputy fields map to JSON Schema 'number'."""
        client = _make_client(_info({"MyFloat": "Float"}))
        schema, _ = get_schema(client, "Employee")
        self.assertEqual(schema["properties"]["MyFloat"], {"type": ["null", "number"]})

    def test_varchar_field_maps_to_string_type(self):
        """VarChar Deputy fields map to JSON Schema 'string'."""
        client = _make_client(_info({"MyStr": "VarChar"}))
        schema, _ = get_schema(client, "Employee")
        self.assertEqual(schema["properties"]["MyStr"], {"type": ["null", "string"]})

    def test_blob_field_maps_to_string_type(self):
        """Blob Deputy fields map to JSON Schema 'string'."""
        client = _make_client(_info({"MyBlob": "Blob"}))
        schema, _ = get_schema(client, "Employee")
        self.assertEqual(schema["properties"]["MyBlob"], {"type": ["null", "string"]})

    def test_bit_field_maps_to_boolean_type(self):
        """Bit Deputy fields map to JSON Schema 'boolean'."""
        client = _make_client(_info({"MyBool": "Bit"}))
        schema, _ = get_schema(client, "Employee")
        self.assertEqual(schema["properties"]["MyBool"], {"type": ["null", "boolean"]})

    def test_time_field_maps_to_string_type(self):
        """Time Deputy fields map to JSON Schema 'string'."""
        client = _make_client(_info({"MyTime": "Time"}))
        schema, _ = get_schema(client, "Employee")
        self.assertEqual(schema["properties"]["MyTime"], {"type": ["null", "string"]})

    def test_date_field_has_date_time_format(self):
        """Date Deputy fields produce type string with format date-time."""
        client = _make_client(_info({"Created": "Date"}))
        schema, _ = get_schema(client, "Employee")
        self.assertEqual(
            schema["properties"]["Created"],
            {"type": ["null", "string"], "format": "date-time"},
        )

    def test_datetime_field_has_date_time_format(self):
        """DateTime Deputy fields produce type string with format date-time."""
        client = _make_client(_info({"Modified": "DateTime"}))
        schema, _ = get_schema(client, "Employee")
        self.assertEqual(
            schema["properties"]["Modified"],
            {"type": ["null", "string"], "format": "date-time"},
        )

    def test_json_field_is_excluded(self):
        """Json-typed fields are silently skipped."""
        client = _make_client(_info({"Data": "Json", "Id": "Integer"}))
        schema, _ = get_schema(client, "Employee")
        self.assertNotIn("Data", schema["properties"])

    def test_unknown_type_is_excluded(self):
        """Fields with unrecognised types are skipped (with a warning)."""
        client = _make_client(_info({"Mystery": "UberType", "Id": "Integer"}))
        with patch("tap_deputy.discover.LOGGER") as mock_log:
            schema, _ = get_schema(client, "Employee")
        self.assertNotIn("Mystery", schema["properties"])
        mock_log.warning.assert_called_once()


# ---------------------------------------------------------------------------
# get_schema – schema structure
# ---------------------------------------------------------------------------

class TestGetSchemaStructure(unittest.TestCase):

    def test_schema_has_additional_properties_false(self):
        """The returned schema always has additionalProperties: false."""
        client = _make_client(_info({"Id": "Integer"}))
        schema, _ = get_schema(client, "Employee")
        self.assertFalse(schema["additionalProperties"])

    def test_schema_type_is_object(self):
        """The returned schema top-level type is 'object'."""
        client = _make_client(_info({"Id": "Integer"}))
        schema, _ = get_schema(client, "Employee")
        self.assertEqual(schema["type"], "object")

    def test_calls_correct_info_endpoint(self):
        """get_schema requests the Deputy /INFO endpoint for the given resource."""
        client = _make_client(_info({}))
        get_schema(client, "Roster")
        client.get.assert_called_once_with(
            "/api/v1/resource/Roster/INFO", endpoint="resource_info"
        )


# ---------------------------------------------------------------------------
# get_schema – metadata
# ---------------------------------------------------------------------------

class TestGetSchemaMetadata(unittest.TestCase):

    def _get_root_metadata(self, metadata):
        return next(m["metadata"] for m in metadata if m["breadcrumb"] == [])

    def _get_field_metadata(self, metadata, field):
        return next(
            m["metadata"]
            for m in metadata
            if m["breadcrumb"] == ["properties", field]
        )

    def test_root_metadata_has_incremental_replication(self):
        """Root metadata specifies INCREMENTAL replication method."""
        client = _make_client(_info({}))
        _, metadata = get_schema(client, "Employee")
        root = self._get_root_metadata(metadata)
        self.assertEqual(root["forced-replication-method"], "INCREMENTAL")

    def test_root_metadata_has_modified_replication_key(self):
        """Root metadata lists Modified as the valid replication key."""
        client = _make_client(_info({}))
        _, metadata = get_schema(client, "Employee")
        root = self._get_root_metadata(metadata)
        self.assertIn("Modified", root["valid-replication-keys"])

    def test_root_metadata_has_resource_name(self):
        """Root metadata stores the Deputy resource name."""
        client = _make_client(_info({}))
        _, metadata = get_schema(client, "Employee")
        root = self._get_root_metadata(metadata)
        self.assertEqual(root["tap-deputy.resource"], "Employee")

    def test_id_field_has_automatic_inclusion(self):
        """The Id field gets inclusion=automatic in metadata."""
        client = _make_client(_info({"Id": "Integer"}))
        _, metadata = get_schema(client, "Employee")
        self.assertEqual(
            self._get_field_metadata(metadata, "Id")["inclusion"], "automatic"
        )

    def test_modified_field_has_automatic_inclusion(self):
        """The Modified field gets inclusion=automatic in metadata."""
        client = _make_client(_info({"Modified": "DateTime"}))
        _, metadata = get_schema(client, "Employee")
        self.assertEqual(
            self._get_field_metadata(metadata, "Modified")["inclusion"], "automatic"
        )

    def test_other_field_has_available_inclusion(self):
        """Non-key fields get inclusion=available in metadata."""
        client = _make_client(_info({"FirstName": "VarChar"}))
        _, metadata = get_schema(client, "Employee")
        self.assertEqual(
            self._get_field_metadata(metadata, "FirstName")["inclusion"], "available"
        )


# ---------------------------------------------------------------------------
# discover()
# ---------------------------------------------------------------------------

class TestDiscover(unittest.TestCase):

    def _make_discover_client(self):
        """Client whose get() returns a minimal INFO response for every resource."""
        client = MagicMock()
        client.get.return_value = {"fields": {"Id": "Integer", "Modified": "DateTime"}}
        return client

    def test_discover_returns_catalog(self):
        """discover() returns a Singer Catalog object."""
        client = self._make_discover_client()
        catalog = discover(client)
        self.assertIsInstance(catalog, Catalog)

    def test_discover_returns_all_resources_as_streams(self):
        """Catalog contains one entry per RESOURCES entry."""
        client = self._make_discover_client()
        catalog = discover(client)
        self.assertEqual(len(catalog.streams), len(RESOURCES))

    def test_each_stream_has_id_as_key_property(self):
        """All catalog entries use ['Id'] as key_properties."""
        client = self._make_discover_client()
        catalog = discover(client)
        for entry in catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                self.assertEqual(entry.key_properties, ["Id"])

    def test_stream_names_match_resources_values(self):
        """tap_stream_id values match the lowercase names in RESOURCES."""
        client = self._make_discover_client()
        catalog = discover(client)
        discovered_ids = {e.tap_stream_id for e in catalog.streams}
        expected_ids = set(RESOURCES.values())
        self.assertEqual(discovered_ids, expected_ids)

    def test_each_stream_has_schema_properties(self):
        """Every catalog entry has a non-empty schema with 'properties'."""
        client = self._make_discover_client()
        catalog = discover(client)
        for entry in catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                schema_dict = entry.schema.to_dict()
                self.assertIn("properties", schema_dict)
                self.assertGreater(len(schema_dict["properties"]), 0)

    def test_each_stream_has_metadata(self):
        """Every catalog entry has a non-empty metadata list."""
        client = self._make_discover_client()
        catalog = discover(client)
        for entry in catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                self.assertIsInstance(entry.metadata, list)
                self.assertGreater(len(entry.metadata), 0)


if __name__ == "__main__":
    unittest.main()
