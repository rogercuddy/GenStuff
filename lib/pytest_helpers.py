"""Pytest Helper Functions - Integration utilities for CSV testing.

This module provides pytest fixtures and helper functions to easily integrate
CSV analysis and test data generation into pytest test suites. Use these helpers
to create parameterized tests with generated CSV data.

Typical usage example in test files:
    from pytest_helpers import csv_test_data, load_csv_config
    
    @pytest.mark.parametrize('test_csv', csv_test_data('config.json', rows=100))
    def test_csv_parser(test_csv):
        result = parse_csv(test_csv)
        assert result is not None
"""

import csv
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Union

import pytest

from lib.csv_analyzer_lib import (
    CSVAnalyzer,
    CSVConfiguration,
    DataGenerator,
)


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def csv_analyzer() -> CSVAnalyzer:
    """Fixture providing a CSV analyzer instance.
    
    Returns:
        CSVAnalyzer instance ready for use.
    """
    return None  # Will be created with specific file in tests


@pytest.fixture
def csv_config(request) -> CSVConfiguration:
    """Fixture that loads a CSV configuration from a path provided via indirect parametrization.
    
    Usage:
        @pytest.mark.parametrize('csv_config', ['path/to/config.json'], indirect=True)
        def test_something(csv_config):
            assert csv_config.line_count > 0
    
    Args:
        request: Pytest request fixture providing the config path.
        
    Returns:
        Loaded CSVConfiguration instance.
    """
    config_path = request.param
    return CSVConfiguration.load(config_path)


@pytest.fixture
def csv_generator(csv_config: CSVConfiguration, request) -> DataGenerator:
    """Fixture providing a data generator based on a configuration.
    
    Usage:
        @pytest.mark.parametrize('csv_config', ['config.json'], indirect=True)
        def test_generation(csv_config, csv_generator):
            rows = csv_generator.generate_rows(10)
            assert len(rows) == 10
    
    Args:
        csv_config: CSV configuration fixture.
        request: Pytest request fixture (can provide seed via param).
        
    Returns:
        DataGenerator instance.
    """
    seed = getattr(request, 'param', None)
    return DataGenerator(config=csv_config, seed=seed)


@pytest.fixture
def temp_csv_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Fixture providing a temporary CSV file path.
    
    The file is automatically cleaned up after the test.
    
    Args:
        tmp_path: Pytest tmp_path fixture.
        
    Yields:
        Path to temporary CSV file.
    """
    csv_file = tmp_path / "test_data.csv"
    yield csv_file
    
    # Cleanup happens automatically with tmp_path


@pytest.fixture
def generated_csv(
    csv_config: CSVConfiguration,
    csv_generator: DataGenerator,
    temp_csv_file: Path,
    request
) -> Path:
    """Fixture that generates a temporary CSV file for testing.
    
    Usage:
        @pytest.mark.parametrize('csv_config', ['config.json'], indirect=True)
        def test_parser(generated_csv):
            with open(generated_csv) as f:
                data = parse(f)
            assert data
    
    Args:
        csv_config: CSV configuration fixture.
        csv_generator: Data generator fixture.
        temp_csv_file: Temporary file path fixture.
        request: Pytest request fixture (can provide num_rows via param).
        
    Returns:
        Path to generated CSV file.
    """
    num_rows = getattr(request, 'param', 100)
    
    csv_generator.generate_csv(
        output_path=temp_csv_file,
        num_rows=num_rows,
        include_header=csv_config.has_header
    )
    
    return temp_csv_file


# ============================================================================
# Helper Functions
# ============================================================================


def load_csv_config(config_path: Union[str, Path]) -> CSVConfiguration:
    """Load a CSV configuration from a file.
    
    Args:
        config_path: Path to configuration JSON file.
        
    Returns:
        Loaded CSVConfiguration instance.
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist.
    """
    return CSVConfiguration.load(config_path)


def analyze_csv_for_test(csv_path: Union[str, Path]) -> CSVConfiguration:
    """Analyze a CSV file and return configuration (convenience function).
    
    Args:
        csv_path: Path to CSV file to analyze.
        
    Returns:
        CSVConfiguration from analysis.
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist.
        ValueError: If CSV cannot be parsed.
    """
    analyzer = CSVAnalyzer(filepath=csv_path)
    return analyzer.analyze()


def generate_test_csv_data(
    config: CSVConfiguration,
    num_rows: int = 100,
    seed: Optional[int] = None
) -> List[List[str]]:
    """Generate test CSV rows without writing to file.
    
    Args:
        config: CSV configuration to use.
        num_rows: Number of rows to generate.
        seed: Optional random seed for reproducibility.
        
    Returns:
        List of rows, where each row is a list of string values.
    """
    generator = DataGenerator(config=config, seed=seed)
    return generator.generate_rows(num_rows)


def create_test_csv_file(
    config: CSVConfiguration,
    output_path: Union[str, Path],
    num_rows: int = 100,
    seed: Optional[int] = None,
    include_header: Optional[bool] = None
) -> Path:
    """Create a test CSV file from configuration.
    
    Args:
        config: CSV configuration to use.
        output_path: Where to write the CSV file.
        num_rows: Number of data rows to generate.
        seed: Optional random seed for reproducibility.
        include_header: Whether to include header (None = use config default).
        
    Returns:
        Path to created CSV file.
    """
    output_path = Path(output_path)
    
    if include_header is None:
        include_header = config.has_header
    
    generator = DataGenerator(config=config, seed=seed)
    generator.generate_csv(
        output_path=output_path,
        num_rows=num_rows,
        include_header=include_header
    )
    
    return output_path


def csv_test_data_generator(
    config_path: Union[str, Path],
    num_files: int = 1,
    rows_per_file: int = 100,
    seed: Optional[int] = None
) -> Generator[Path, None, None]:
    """Generator that yields temporary CSV files for testing.
    
    Usage:
        for csv_file in csv_test_data_generator('config.json', num_files=5):
            result = process_csv(csv_file)
            assert result.is_valid
    
    Args:
        config_path: Path to configuration file.
        num_files: Number of CSV files to generate.
        rows_per_file: Number of rows in each file.
        seed: Optional random seed.
        
    Yields:
        Path objects to temporary CSV files.
    """
    config = load_csv_config(config_path)
    generator = DataGenerator(config=config, seed=seed)
    
    for i in range(num_files):
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.csv',
            delete=False,
            newline=''
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
            # Generate the CSV
            generator.generate_csv(
                output_path=tmp_path,
                num_rows=rows_per_file,
                include_header=config.has_header
            )
            
            yield tmp_path
            
            # Cleanup
            tmp_path.unlink()


def validate_csv_structure(
    csv_path: Union[str, Path],
    config: CSVConfiguration
) -> Dict[str, Any]:
    """Validate that a CSV file matches the expected configuration.
    
    Useful for testing that generated CSVs conform to specifications.
    
    Args:
        csv_path: Path to CSV file to validate.
        config: Expected configuration.
        
    Returns:
        Dictionary with validation results:
            - 'valid': bool indicating overall validity
            - 'errors': list of error messages
            - 'warnings': list of warning messages
            - 'stats': statistics about the validation
    """
    errors = []
    warnings = []
    stats = {
        'rows_checked': 0,
        'columns_checked': 0,
    }
    
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        errors.append(f"File not found: {csv_path}")
        return {
            'valid': False,
            'errors': errors,
            'warnings': warnings,
            'stats': stats
        }
    
    try:
        with open(csv_path, 'r', encoding=config.encoding, newline='') as f:
            reader = csv.reader(
                f,
                delimiter=config.delimiter,
                quotechar=config.quotechar
            )
            
            rows = list(reader)
            stats['rows_checked'] = len(rows)
            
            if not rows:
                errors.append("CSV file is empty")
                return {
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'stats': stats
                }
            
            # Check header if expected
            if config.has_header:
                header = rows[0]
                expected_header = [col.name for col in config.columns]
                
                if header != expected_header:
                    errors.append(
                        f"Header mismatch. Expected: {expected_header}, Got: {header}"
                    )
                
                data_rows = rows[1:]
            else:
                data_rows = rows
            
            # Check number of columns
            expected_col_count = len(config.columns)
            stats['columns_checked'] = expected_col_count
            
            for row_idx, row in enumerate(data_rows, start=1):
                if len(row) != expected_col_count:
                    errors.append(
                        f"Row {row_idx}: Expected {expected_col_count} columns, "
                        f"got {len(row)}"
                    )
                    
                    # Only report first few column count errors
                    if len([e for e in errors if 'Expected' in e]) > 5:
                        errors.append("... (additional column count errors omitted)")
                        break
            
            # Check for empty file
            if not data_rows:
                warnings.append("No data rows found (only header)")
        
    except Exception as e:
        errors.append(f"Error reading CSV: {e}")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'stats': stats
    }


def create_parameterized_test_data(
    config_path: Union[str, Path],
    variations: List[Dict[str, Any]]
) -> List[Path]:
    """Create multiple test CSV files with different parameters.
    
    Useful for parameterized testing with different data characteristics.
    
    Args:
        config_path: Path to base configuration.
        variations: List of dicts with keys 'num_rows', 'seed', 'output_path'.
        
    Returns:
        List of paths to created CSV files.
        
    Example:
        variations = [
            {'num_rows': 10, 'seed': 1, 'output_path': 'test_small.csv'},
            {'num_rows': 1000, 'seed': 2, 'output_path': 'test_large.csv'},
        ]
        files = create_parameterized_test_data('config.json', variations)
    """
    config = load_csv_config(config_path)
    created_files = []
    
    for variation in variations:
        output_path = variation.get('output_path')
        if not output_path:
            # Create temp file if no path specified
            tmp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.csv',
                delete=False
            )
            output_path = tmp_file.name
            tmp_file.close()
        
        num_rows = variation.get('num_rows', 100)
        seed = variation.get('seed')
        
        csv_path = create_test_csv_file(
            config=config,
            output_path=output_path,
            num_rows=num_rows,
            seed=seed
        )
        
        created_files.append(csv_path)
    
    return created_files


# ============================================================================
# Assertion Helpers
# ============================================================================


def assert_csv_readable(csv_path: Union[str, Path], encoding: str = 'utf-8') -> None:
    """Assert that a CSV file is readable and has valid structure.
    
    Args:
        csv_path: Path to CSV file.
        encoding: File encoding to use.
        
    Raises:
        AssertionError: If CSV is not readable or invalid.
    """
    csv_path = Path(csv_path)
    
    assert csv_path.exists(), f"CSV file does not exist: {csv_path}"
    assert csv_path.stat().st_size > 0, f"CSV file is empty: {csv_path}"
    
    with open(csv_path, 'r', encoding=encoding) as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        assert len(rows) > 0, "CSV contains no rows"


def assert_csv_row_count(
    csv_path: Union[str, Path],
    expected_count: int,
    has_header: bool = True
) -> None:
    """Assert that a CSV has the expected number of data rows.
    
    Args:
        csv_path: Path to CSV file.
        expected_count: Expected number of data rows.
        has_header: Whether file has a header row to exclude from count.
        
    Raises:
        AssertionError: If row count doesn't match.
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        actual_count = len(rows)
        if has_header:
            actual_count -= 1
        
        assert actual_count == expected_count, (
            f"Expected {expected_count} data rows, got {actual_count}"
        )


def assert_csv_columns(
    csv_path: Union[str, Path],
    expected_columns: List[str]
) -> None:
    """Assert that a CSV has the expected column headers.
    
    Args:
        csv_path: Path to CSV file.
        expected_columns: List of expected column names.
        
    Raises:
        AssertionError: If columns don't match.
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        assert header == expected_columns, (
            f"Expected columns {expected_columns}, got {header}"
        )
