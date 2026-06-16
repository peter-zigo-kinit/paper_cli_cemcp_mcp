"""Tests that Unit Converter publishes typed outputSchema for all tools."""

import asyncio

import pytest

from unit_converter_mcp.server import app

EXPECTED_TOOL_NAMES = {
    "convert_temperature",
    "convert_angle",
    "convert_length",
    "convert_energy",
    "convert_force",
    "convert_pressure",
    "convert_power",
    "convert_speed",
    "convert_area",
    "convert_mass",
    "convert_volume",
    "convert_computer_data",
    "convert_density",
    "convert_time",
    "convert_batch",
    "list_supported_units",
}

SINGLE_CONVERSION_PROPERTIES = {
    "original_value",
    "original_unit",
    "converted_value",
    "converted_unit",
    "conversion_type",
}


def _schema_properties(output_schema: dict) -> dict:
    return output_schema.get("properties", {})


def _is_generic_object_schema(output_schema: dict) -> bool:
    return (
        output_schema.get("type") == "object"
        and output_schema.get("additionalProperties") is True
        and not output_schema.get("properties")
    )


@pytest.fixture
def output_schemas_by_name():
    async def _load():
        tools = await app._tool_manager.get_tools()
        return {
            name: tool.to_mcp_tool().outputSchema
            for name, tool in tools.items()
        }

    return asyncio.run(_load())


def test_publishes_sixteen_tools(output_schemas_by_name):
    assert set(output_schemas_by_name) == EXPECTED_TOOL_NAMES


def test_single_conversion_tools_have_conversion_result_schema(output_schemas_by_name):
    single_tools = EXPECTED_TOOL_NAMES - {"convert_batch", "list_supported_units"}
    for name in single_tools:
        schema = output_schemas_by_name[name]
        assert not _is_generic_object_schema(schema), f"{name} still has generic schema"
        props = set(_schema_properties(schema))
        assert SINGLE_CONVERSION_PROPERTIES <= props


def test_convert_batch_schema(output_schemas_by_name):
    props = _schema_properties(output_schemas_by_name["convert_batch"])
    assert "batch_results" in props
    assert "summary" in props


def test_list_supported_units_schema(output_schemas_by_name):
    props = _schema_properties(output_schemas_by_name["list_supported_units"])
    assert "length" in props
    assert "temperature" in props
