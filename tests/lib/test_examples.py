"""Example pytest tests demonstrating CSV analyzer and generator usage.

This module shows various patterns for using the CSV analysis and generation
tools in pytest test suites. These examples can be adapted for real-world
testing scenarios.
"""

import csv
from pathlib import Path
from typing import List

import pytest

from lib.csv_analyzer_lib import (
    CSVAnalyzer,
    CSVConfiguration,
    DataGenerator,
    DataType,
)
from lib.pytest_helpers import (
    analyze_csv_for_test,
    assert_csv_columns,
    assert_csv_readable,
    assert_csv_row_count,
    create_test_csv_file,
    csv_test_data_generator,
    generate_test_csv_data,
    load_csv_config,
    validate_csv_structure,
)


# ============================================================================
# Example Test Class: Basic CSV Parser Testing
# ============================================================================


class TestCSVParser:
    """Example tests for a CSV parser using generated test data.
    
    These tests demonstrate how to use the CSV analyzer and generator
    to create comprehensive test cases for CSV parsing code.
    """
    
    @pytest.fixture
    def sample_config(self, tmp_path: Path) -> Path:
        """Create a sample configuration for testing.

        Args:
            tmp_path: Pytest temporary directory fixture.
            
        Returns:
            Path to configuration file.
        """
        # Create a sample CSV to analyze
        sample_csv = tmp_path / "sample.csv"
        with open(sample_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'age', 'email'])
            writer.writerow(['1', 'John Doe', '30', 'john@example.com'])
            writer.writerow(['2', 'Jane Smith', '25', 'jane@example.com'])
            writer.writerow(['3', 'Bob Johnson', '35', 'bob@example.com'])
        
        # Analyze it
        analyzer = CSVAnalyzer(sample_csv)
        config = analyzer.analyze()
        
        # Save config
        config_path = tmp_path / "sample_config.json"
        config.save(config_path)
        
        return config_path
    
    def test_parse_csv_structure(self, sample_config: Path, tmp_path: Path) -> None:
        """Test that parser correctly reads CSV structure."""
        # Generate test CSV
        config = load_csv_config(sample_config)
        test_csv = create_test_csv_file(
            config=config,
            output_path=tmp_path / "test.csv",
            num_rows=10,
            seed=42
        )
        
        # Verify CSV is readable
        assert_csv_readable(test_csv)
        assert_csv_row_count(test_csv, expected_count=10, has_header=True)
        
        # Parse CSV (example parser)
        with open(test_csv, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Assertions about parsed data
        assert len(rows) == 10
        assert all('id' in row for row in rows)
        assert all('name' in row for row in rows)
    
    def test_parse_csv_with_different_sizes(
        self,
        sample_config: Path,
        tmp_path: Path
    ) -> None:
        """Test parser with various CSV sizes."""
        config = load_csv_config(sample_config)
        
        # Test with different row counts
        for num_rows in [1, 10, 100, 1000]:
            test_csv = tmp_path / f"test_{num_rows}.csv"
            create_test_csv_file(
                config=config,
                output_path=test_csv,
                num_rows=num_rows,
                seed=42
            )
            
            # Parse and verify
            with open(test_csv, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == num_rows
    
    def test_parse_empty_columns(self, sample_config: Path, tmp_path: Path) -> None:
        """Test parser handles empty/null values correctly."""
        # Generate data that may contain nulls
        config = load_csv_config(sample_config)
        test_csv = create_test_csv_file(
            config=config,
            output_path=tmp_path / "test_nulls.csv",
            num_rows=50,
            seed=123
        )
        
        # Parse and check for nulls
        with open(test_csv, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Verify parser handles empty values
        for row in rows:
            for key, value in row.items():
                # Empty values should be represented consistently
                assert value is not None  # Parser should not fail


# ============================================================================
# Example Test Class: Data Validation Testing
# ============================================================================


class TestDataValidator:
    """Example tests for data validation using generated test data."""
    
    def example_validate_row(self, row: dict) -> List[str]:
        """Example validation function to test.
        
        Args:
            row: Dictionary representing a CSV row.
            
        Returns:
            List of validation errors (empty if valid).
        """
        errors = []
        
        # Example validations
        if 'id' in row and row['id']:
            try:
                int(row['id'])
            except ValueError:
                errors.append(f"Invalid id: {row['id']}")
        
        if 'email' in row and row['email']:
            if '@' not in row['email']:
                errors.append(f"Invalid email: {row['email']}")
        
        return errors
    
    @pytest.fixture
    def validation_config(self, tmp_path: Path) -> CSVConfiguration:
        """Create a configuration for validation testing.
        
        Args:
            tmp_path: Pytest temporary directory fixture.
            
        Returns:
            CSVConfiguration for testing.
        """
        # Create sample CSV with various data types
        sample_csv = tmp_path / "validation_sample.csv"
        with open(sample_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'email', 'phone', 'amount'])
            writer.writerow(['1', 'user@example.com', '555-1234', '100.50'])
            writer.writerow(['2', 'admin@test.com', '555-5678', '250.00'])
        
        analyzer = CSVAnalyzer(sample_csv)
        return analyzer.analyze()
    
    def test_validate_generated_data(
        self,
        validation_config: CSVConfiguration,
        tmp_path: Path
    ) -> None:
        """Test that generated data passes validation."""
        # Generate test data
        rows = generate_test_csv_data(
            config=validation_config,
            num_rows=100,
            seed=42
        )
        
        # Skip header if present
        if validation_config.has_header:
            header = rows[0]
            data_rows = rows[1:]
        else:
            header = [col.name for col in validation_config.columns]
            data_rows = rows
        
        # Validate each row
        for row_values in data_rows:
            row_dict = dict(zip(header, row_values))
            errors = self.example_validate_row(row_dict)
            
            # Generated data should pass validation
            # (In real tests, you'd have specific validation rules)
            assert isinstance(errors, list)
    
    @pytest.mark.parametrize('seed', [42, 123, 456])
    def test_validate_with_different_seeds(
        self,
        validation_config: CSVConfiguration,
        seed: int
    ) -> None:
        """Test validation with different random seeds."""
        rows = generate_test_csv_data(
            config=validation_config,
            num_rows=50,
            seed=seed
        )
        
        # Should generate different data with different seeds
        assert len(rows) > 0


# ============================================================================
# Example Test Class: Configuration Comparison
# ============================================================================


class TestConfigurationAnalysis:
    """Tests for analyzing and comparing CSV configurations."""
    
    def test_analyze_csv_detects_types(self, tmp_path: Path) -> None:
        """Test that analyzer correctly detects data types."""
        # Create CSV with various types
        test_csv = tmp_path / "types.csv"
        with open(test_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['int_col', 'float_col', 'string_col', 'email_col'])
            writer.writerow(['1', '1.5', 'hello', 'user@test.com'])
            writer.writerow(['2', '2.5', 'world', 'admin@test.com'])
            writer.writerow(['3', '3.5', 'test', 'info@test.com'])
        
        # Analyze
        config = analyze_csv_for_test(test_csv)
        
        # Verify detected types
        assert config.get_column('int_col').data_type == DataType.INTEGER
        assert config.get_column('float_col').data_type == DataType.FLOAT
        assert config.get_column('email_col').data_type == DataType.EMAIL
    
    def test_configuration_saves_and_loads(self, tmp_path: Path) -> None:
        """Test that configuration can be saved and loaded correctly."""
        # Create and analyze CSV
        test_csv = tmp_path / "test.csv"
        with open(test_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'value'])
            writer.writerow(['1', 'test'])
        
        config1 = analyze_csv_for_test(test_csv)
        
        # Save configuration
        config_path = tmp_path / "config.json"
        config1.save(config_path)
        
        # Load configuration
        config2 = load_csv_config(config_path)
        
        # Verify they match
        assert config1.delimiter == config2.delimiter
        assert len(config1.columns) == len(config2.columns)
        assert config1.has_header == config2.has_header
    
    def test_validate_generated_csv_structure(
        self,
        tmp_path: Path
    ) -> None:
        """Test that generated CSV matches configuration."""
        # Create original CSV
        original_csv = tmp_path / "original.csv"
        with open(original_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'score'])
            writer.writerow(['1', 'Alice', '95'])
            writer.writerow(['2', 'Bob', '87'])
        
        # Analyze and generate
        config = analyze_csv_for_test(original_csv)
        generated_csv = tmp_path / "generated.csv"
        
        create_test_csv_file(
            config=config,
            output_path=generated_csv,
            num_rows=10,
            seed=42
        )
        
        # Validate structure
        validation_result = validate_csv_structure(generated_csv, config)
        
        assert validation_result['valid'], (
            f"Validation errors: {validation_result['errors']}"
        )
        assert validation_result['stats']['rows_checked'] == 11  # Header + 10 data rows


# ============================================================================
# Example Test Class: Parameterized Testing with CSV Generator
# ============================================================================


class TestParameterizedCSVProcessing:
    """Examples of parameterized tests using CSV generator."""
    
    @pytest.fixture
    def multi_type_config(self, tmp_path: Path) -> Path:
        """Configuration with multiple data types."""
        csv_file = tmp_path / "multi_type.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'date', 'amount', 'status'])
            writer.writerow(['1', '2024-01-01', '100.00', 'active'])
            writer.writerow(['2', '2024-01-02', '200.00', 'inactive'])
        
        config = analyze_csv_for_test(csv_file)
        config_path = tmp_path / "multi_type_config.json"
        config.save(config_path)
        return config_path
    
    @pytest.mark.parametrize('num_rows', [10, 50, 100])
    def test_process_varying_sizes(
        self,
        multi_type_config: Path,
        num_rows: int,
        tmp_path: Path
    ) -> None:
        """Test processing CSVs of different sizes."""
        config = load_csv_config(multi_type_config)
        
        test_csv = tmp_path / f"test_{num_rows}.csv"
        create_test_csv_file(
            config=config,
            output_path=test_csv,
            num_rows=num_rows,
            seed=42
        )
        
        # Process CSV
        with open(test_csv, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == num_rows
    
    @pytest.mark.parametrize('seed', [1, 2, 3])
    def test_reproducible_generation(
        self,
        multi_type_config: Path,
        seed: int,
        tmp_path: Path
    ) -> None:
        """Test that same seed produces same data."""
        config = load_csv_config(multi_type_config)
        
        # Generate twice with same seed
        rows1 = generate_test_csv_data(config, num_rows=10, seed=seed)
        rows2 = generate_test_csv_data(config, num_rows=10, seed=seed)
        
        assert rows1 == rows2
    
    def test_generator_iteration(self, multi_type_config: Path) -> None:
        """Test iterating through multiple generated files."""
        generated_files = []
        
        for csv_path in csv_test_data_generator(
            multi_type_config,
            num_files=3,
            rows_per_file=20,
            seed=42
        ):
            # Each iteration provides a new CSV file
            assert csv_path.exists()
            
            # Process the file
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                assert len(rows) > 0
            
            generated_files.append(csv_path)
        
        # Verify we got expected number of files
        assert len(generated_files) == 3


# ============================================================================
# Example: Testing Custom CSV Parser Function
# ============================================================================


def parse_financial_csv(csv_path: Path) -> List[dict]:
    """Example CSV parser function to test.
    
    Args:
        csv_path: Path to CSV file.
        
    Returns:
        List of parsed records.
    """
    records = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            record = {
                'id': int(row.get('id', 0)),
                'amount': float(row.get('amount', 0.0)),
                'date': row.get('date', ''),
                'description': row.get('description', '')
            }
            records.append(record)
    
    return records


class TestFinancialCSVParser:
    """Tests for the financial CSV parser using generated data."""
    
    @pytest.fixture
    def financial_config(self, tmp_path: Path) -> Path:
        """Create configuration for financial CSV."""
        csv_file = tmp_path / "financial.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'amount', 'date', 'description'])
            writer.writerow(['1', '1500.00', '2024-01-01', 'Purchase'])
            writer.writerow(['2', '2500.50', '2024-01-02', 'Sale'])
        
        config = analyze_csv_for_test(csv_file)
        config_path = tmp_path / "financial_config.json"
        config.save(config_path)
        return config_path
    
    def test_parser_returns_correct_count(
        self,
        financial_config: Path,
        tmp_path: Path
    ) -> None:
        """Test parser returns correct number of records."""
        config = load_csv_config(financial_config)
        
        test_csv = tmp_path / "test.csv"
        create_test_csv_file(
            config=config,
            output_path=test_csv,
            num_rows=25,
            seed=42
        )
        
        records = parse_financial_csv(test_csv)
        assert len(records) == 25
    
    def test_parser_handles_various_amounts(
        self,
        financial_config: Path,
        tmp_path: Path
    ) -> None:
        """Test parser correctly handles different amount values."""
        config = load_csv_config(financial_config)
        
        test_csv = tmp_path / "test.csv"
        create_test_csv_file(
            config=config,
            output_path=test_csv,
            num_rows=100,
            seed=42
        )
        
        records = parse_financial_csv(test_csv)
        
        # Verify all amounts are parsed as floats
        for record in records:
            assert isinstance(record['amount'], float)
            assert record['amount'] >= 0
    
    @pytest.mark.parametrize('num_records', [1, 10, 100, 1000])
    def test_parser_performance(
        self,
        financial_config: Path,
        tmp_path: Path,
        num_records: int
    ) -> None:
        """Test parser performance with different data sizes."""
        config = load_csv_config(financial_config)
        
        test_csv = tmp_path / f"test_{num_records}.csv"
        create_test_csv_file(
            config=config,
            output_path=test_csv,
            num_rows=num_records,
            seed=42
        )
        
        # Time the parsing
        import time
        start = time.time()
        records = parse_financial_csv(test_csv)
        elapsed = time.time() - start
        
        assert len(records) == num_records
        # Should complete in reasonable time (adjust threshold as needed)
        assert elapsed < 10.0
