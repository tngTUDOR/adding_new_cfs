"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

import pytest

# Add parent directory to Python path so we can import add_new_cfs
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_csv_path() -> Path:
    """
    Return the path to the sample medical substances CSV file.

    Returns
    -------
    Path
        Path to the sample CSV fixture file.
    """
    return Path(__file__).parent / "fixtures" / "sample_medical_substances.csv"

