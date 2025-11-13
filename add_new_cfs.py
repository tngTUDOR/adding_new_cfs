from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from bw2data import Database
import bw2data as bd


def _coerce_to_path(path: str | Path) -> Path:
    """
    Convert a string or Path object to a Path object.

    Parameters
    ----------
    path:
        A string or Path object representing a file path.

    Returns
    -------
    Path
        A Path object representing the input path.
    """
    if isinstance(path, Path):
        return path
    return Path(path)


def _parse_categories(raw: str, *, line_number: int) -> tuple[str, ...]:
    """
    Parse a categories string into a tuple of category segments.

    The categories string should be separated by "::" (e.g., "air::low urban::population").
    Empty strings result in an empty tuple.

    Parameters
    ----------
    raw:
        The raw categories string from the CSV file.
    line_number:
        The line number in the CSV file (for error reporting).

    Returns
    -------
    tuple[str, ...]
        A tuple of category segments, or an empty tuple if the input is empty.

    Raises
    ------
    ValueError
        If the categories string is malformed (empty after parsing).
    """
    if raw.strip() == "":
        return tuple()

    parts = tuple(segment.strip() for segment in raw.split("::") if segment.strip())
    if not parts:
        raise ValueError(f"Row {line_number}: categories column is malformed.")

    return parts


def _sanitize_code(name: str) -> str:
    """
    Sanitize a flow name to create a code by replacing spaces with underscores.

    Parameters
    ----------
    name:
        The flow name to sanitize.

    Returns
    -------
    str
        The sanitized code with spaces replaced by underscores.
    """
    return name.strip().replace(" ", "_")


def _parse_cf(raw: str, *, line_number: int) -> float:
    """
    Parse a characterization factor (CF) value from a string.

    Parameters
    ----------
    raw:
        The raw CF value string from the CSV file.
    line_number:
        The line number in the CSV file (for error reporting).

    Returns
    -------
    float
        The parsed floating point value.

    Raises
    ------
    ValueError
        If the string cannot be converted to a float.
    """
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {line_number}: cf column must contain a floating point value.") from exc


def parse_new_flows_from_csv(path: str | Path) -> list[dict[str, object]]:
    """
    Parse a CSV file containing new flow definitions.

    The CSV file must contain the following columns:
    - new_database: The database name for the new flow
    - flow_name: The name of the flow
    - code: The code for the flow (if empty, flow_name will be used with spaces replaced by underscores)
    - unit: The unit of the flow
    - CAS number: The CAS number (can be empty)
    - categories: Category hierarchy separated by "::" (e.g., "air::low urban::population")
    - cf: The characterization factor as a floating point value

    Examples
    --------
    Example CSV file content:

    .. code-block:: text

        new_database,flow_name,code,unit,CAS number,categories,cf
        additional_chemical_flows,Acetaminophen,acetaminophen,kg,103-90-2,water::surface water::freshwater,1.23E-05
        additional_chemical_flows,Ibuprofen,,kg,15687-27-1,water::surface water::freshwater,2.45E-06
        additional_chemical_flows,Aspirin,aspirin,kg,50-78-2,water::groundwater,3.67E-07
        additional_chemical_flows,Metformin,,kg,657-24-9,water::surface water::freshwater,4.89E-06

    Parameters
    ----------
    path:
        The path to the CSV file (string or Path object).

    Returns
    -------
    list[dict[str, object]]
        A list of dictionaries, one per row. Each dictionary contains:
        - database: The database name (from new_database column)
        - name: The flow name (from flow_name column)
        - code: The flow code (from code column, or sanitized flow_name if code is empty)
        - unit: The unit (from unit column)
        - CAS number: The CAS number (from CAS number column, can be empty string)
        - categories: A tuple of category segments (parsed from categories column)
        - cf: The characterization factor as a float (from cf column)

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    ValueError
        If required columns are missing or if data cannot be parsed correctly.
    """

    csv_path = _coerce_to_path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    required_columns: Sequence[str] = (
        "new_database",
        "flow_name",
        "code",
        "unit",
        "CAS number",
        "categories",
        "cf",
    )

    parsed_rows: list[dict[str, object]] = []

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        missing_columns = [column for column in required_columns if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                f"CSV file must contain the following columns: {', '.join(required_columns)}. "
                f"Missing: {', '.join(missing_columns)}."
            )

        for row_index, row in enumerate(reader, start=2):  # account for header line
            categories = _parse_categories(row.get("categories", ""), line_number=row_index)
            cf = _parse_cf(row.get("cf"), line_number=row_index)
            
            flow_name = row.get("flow_name", "").strip()
            code_raw = row.get("code", "").strip()
            code = code_raw if code_raw else _sanitize_code(flow_name)

            parsed_rows.append(
                {
                    "database": row.get("new_database", "").strip(),
                    "name": flow_name,
                    "code": code,
                    "unit": row.get("unit", "").strip(),
                    "CAS number": (row.get("CAS number") or "").strip(),
                    "categories": categories,
                    "cf": cf,
                }
            )

    return parsed_rows


def parse_node_ids_and_cfs(path: str | Path) -> list[tuple[int, float]]:
    """
    Parse a CSV file and return node IDs and characterization factors.

    This function parses the CSV file, retrieves nodes from the Brightway25 database
    using name and code, and returns a list of tuples containing (node.id, cf).

    The database name is read from the "new_database" column in the CSV file.
    Requires Brightway25.

    Parameters
    ----------
    path:
        The path to the CSV file (string or Path object).

    Returns
    -------
    list[tuple[int, float]]
        A list of tuples, each containing (node.id, cf) for each row in the CSV.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    ValueError
        If required columns are missing, if data cannot be parsed correctly,
        or if the database name is missing or invalid.
    """
    csv_path = _coerce_to_path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    required_columns: Sequence[str] = (
        "new_database",
        "flow_name",
        "code",
        "unit",
        "CAS number",
        "categories",
        "cf",
    )

    node_cf_tuples: list[tuple[int, float]] = []
    database_name: str | None = None

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        missing_columns = [column for column in required_columns if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                f"CSV file must contain the following columns: {', '.join(required_columns)}. "
                f"Missing: {', '.join(missing_columns)}."
            )

        # Get database name from first row
        first_row = next(reader, None)
        if first_row is None:
            raise ValueError("CSV file is empty (no data rows).")
        
        database_name = first_row.get("new_database", "").strip()
        if not database_name:
            raise ValueError("Database name is missing in the 'new_database' column.")
        
        # Process first row
        cf = _parse_cf(first_row.get("cf"), line_number=2)
        flow_name = first_row.get("flow_name", "").strip()
        code_raw = first_row.get("code", "").strip()
        code = code_raw if code_raw else _sanitize_code(flow_name)
        
        # Get the target node using name and code
        node = bd.get_node(name=flow_name, code=code)
        node_cf_tuples.append((node.id, cf))

        # Process remaining rows
        for row_index, row in enumerate(reader, start=3):  # start at 3 (header + first row)
            # Verify database name is consistent
            row_database = row.get("new_database", "").strip()
            if row_database != database_name:
                raise ValueError(
                    f"Row {row_index}: Database name mismatch. Expected '{database_name}', "
                    f"found '{row_database}'. All rows must use the same database."
                )
            
            cf = _parse_cf(row.get("cf"), line_number=row_index)
            
            flow_name = row.get("flow_name", "").strip()
            code_raw = row.get("code", "").strip()
            code = code_raw if code_raw else _sanitize_code(flow_name)

            # Get the target node using name and code
            node = bd.get_node(name=flow_name, code=code)
            
            # Create tuple with node.id and cf value
            node_cf_tuples.append((node.id, cf))

    return node_cf_tuples

