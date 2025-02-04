import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def test_files_dir():
    """Create and return the test files directory path."""
    path = Path("tests/test_files")
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def test_output_dir():
    """Create and return the test output directory path."""
    path = Path("tests/test_output")
    path.mkdir(parents=True, exist_ok=True)
    return path
