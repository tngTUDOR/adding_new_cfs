"""Tests for the parse_new_flows_from_csv function."""

import tempfile
from pathlib import Path

import pytest

from add_new_cfs import parse_new_flows_from_csv


def test_parse_sample_csv(sample_csv_path: Path) -> None:
    """Test parsing the sample medical substances CSV file."""
    result = parse_new_flows_from_csv(sample_csv_path)

    assert len(result) == 10, "Should parse 10 medical substances"

    # Check first substance (Acetaminophen) - has explicit code
    first = result[0]
    assert first["database"] == "additional_chemical_flows"
    assert first["name"] == "Acetaminophen"
    assert first["code"] == "acetaminophen"
    assert first["unit"] == "kg"
    assert first["CAS number"] == "103-90-2"
    assert first["categories"] == ("water", "surface water", "freshwater")
    assert first["cf"] == 1.23e-05

    # Check Ibuprofen (row 2) - has empty code, should use flow_name
    ibuprofen = result[1]
    assert ibuprofen["name"] == "Ibuprofen"
    assert ibuprofen["code"] == "Ibuprofen"  # Empty code, so uses flow_name as-is (no spaces to replace)

    # Check last substance (Warfarin) - empty code, should use sanitized name
    last = result[-1]
    assert last["database"] == "additional_chemical_flows"
    assert last["name"] == "Warfarin"
    assert last["code"] == "Warfarin"  # Empty code, so uses flow_name as-is (no spaces to replace)
    assert last["unit"] == "kg"
    assert last["CAS number"] == "81-81-2"
    assert last["categories"] == ("water", "surface water", "freshwater")
    assert last["cf"] == 1.11e-05


def test_parse_csv_with_empty_cas_number() -> None:
    """Test parsing CSV with empty CAS number."""
    csv_content = """new_database,flow_name,code,unit,CAS number,categories,type,cf
additional_chemical_flows,Test Substance,test_substance,kg,,water::surface water::freshwater,emission,1.0E-05
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        temp_path = Path(f.name)

    try:
        result = parse_new_flows_from_csv(temp_path)
        assert len(result) == 1
        assert result[0]["CAS number"] == ""
    finally:
        temp_path.unlink()


def test_parse_csv_with_string_path(sample_csv_path: Path) -> None:
    """Test that function accepts string path."""
    result = parse_new_flows_from_csv(str(sample_csv_path))
    assert len(result) == 10


def test_parse_csv_with_path_object(sample_csv_path: Path) -> None:
    """Test that function accepts Path object."""
    result = parse_new_flows_from_csv(sample_csv_path)
    assert len(result) == 10


def test_missing_file() -> None:
    """Test that FileNotFoundError is raised for non-existent file."""
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        parse_new_flows_from_csv("nonexistent_file.csv")


def test_missing_required_column() -> None:
    """Test that ValueError is raised when required columns are missing."""
    csv_content = """new_database,flow_name,code,unit,CAS number,categories,type
additional_chemical_flows,Test Substance,test_substance,kg,123-45-6,water::surface water::freshwater,emission
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        temp_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Missing: cf"):
            parse_new_flows_from_csv(temp_path)
    finally:
        temp_path.unlink()


def test_invalid_cf_value() -> None:
    """Test that ValueError is raised for invalid CF values."""
    csv_content = """new_database,flow_name,code,unit,CAS number,categories,type,cf
additional_chemical_flows,Test Substance,test_substance,kg,123-45-6,water::surface water::freshwater,emission,not_a_number
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        temp_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="cf column must contain a floating point value"):
            parse_new_flows_from_csv(temp_path)
    finally:
        temp_path.unlink()


def test_categories_parsing() -> None:
    """Test that categories are correctly parsed into tuples."""
    csv_content = """new_database,flow_name,code,unit,CAS number,categories,type,cf
additional_chemical_flows,Test Substance,test_substance,kg,123-45-6,air::low urban::population,emission,1.0E-05
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        temp_path = Path(f.name)

    try:
        result = parse_new_flows_from_csv(temp_path)
        assert result[0]["categories"] == ("air", "low urban", "population")
    finally:
        temp_path.unlink()


def test_categories_with_whitespace() -> None:
    """Test that categories with whitespace are correctly trimmed."""
    csv_content = """new_database,flow_name,code,unit,CAS number,categories,type,cf
additional_chemical_flows,Test Substance,test_substance,kg,123-45-6, air :: low urban :: population ,emission,1.0E-05
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        temp_path = Path(f.name)

    try:
        result = parse_new_flows_from_csv(temp_path)
        assert result[0]["categories"] == ("air", "low urban", "population")
    finally:
        temp_path.unlink()


def test_code_sanitization_when_empty() -> None:
    """Test that empty code column uses sanitized flow_name."""
    csv_content = """new_database,flow_name,code,unit,CAS number,categories,type,cf
additional_chemical_flows,Test Substance With Spaces,,kg,123-45-6,water::surface water::freshwater,emission,1.0E-05
additional_chemical_flows,Another Test,another_test,kg,123-45-6,water::surface water::freshwater,emission,1.0E-05
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        temp_path = Path(f.name)

    try:
        result = parse_new_flows_from_csv(temp_path)
        assert len(result) == 2
        # First row has empty code, should use sanitized flow_name
        assert result[0]["code"] == "Test_Substance_With_Spaces"
        # Second row has explicit code
        assert result[1]["code"] == "another_test"
    finally:
        temp_path.unlink()


def test_all_medical_substances_have_required_fields(sample_csv_path: Path) -> None:
    """Test that all parsed medical substances have all required fields."""
    result = parse_new_flows_from_csv(sample_csv_path)

    required_keys = {"database", "name", "code", "unit", "CAS number", "categories", "type", "cf"}

    for substance in result:
        assert set(substance.keys()) == required_keys
        assert isinstance(substance["database"], str)
        assert isinstance(substance["name"], str)
        assert isinstance(substance["code"], str)
        assert isinstance(substance["unit"], str)
        assert isinstance(substance["CAS number"], str)
        assert isinstance(substance["categories"], tuple)
        assert isinstance(substance["type"], str)
        assert isinstance(substance["cf"], float)

