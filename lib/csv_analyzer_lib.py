"""CSV Analyzer Library - Core functionality for CSV analysis and test data generation.

This library provides comprehensive tools for analyzing CSV files, detecting data patterns,
and generating synthetic test data that matches the structure and characteristics of the
original data. Designed for use in testing frameworks like pytest.

Typical usage example:
    analyzer = CSVAnalyzer('input.csv')
    config = analyzer.analyze()
    config.save('config.json')
    
    generator = DataGenerator(config)
    generator.generate_csv('test_output.csv', num_rows=100)
"""

import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import random
import string


class DataType(Enum):
    """Enumeration of supported data types for CSV columns."""
    
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    STRING = "string"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    BOOLEAN = "boolean"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    ENUM = "enum"  # Fixed set of values
    MIXED = "mixed"  # Multiple types present
    EMPTY = "empty"  # All null/empty values


@dataclass
class ColumnMetadata:
    """Metadata describing a single CSV column.
    
    Attributes:
        name: Column name/header.
        index: Zero-based column position.
        data_type: Detected data type from DataType enum.
        nullable: Whether column contains null/empty values.
        null_percentage: Percentage of null values (0.0 to 1.0).
        unique_count: Number of unique non-null values.
        total_count: Total number of values analyzed.
        sample_values: Representative sample of actual values.
        patterns: Detected patterns (regex, formats, etc.).
        statistics: Statistical information for numeric types.
        enum_values: Complete set of values if treated as enum.
        max_length: Maximum string length observed.
        min_length: Minimum string length observed.
    """
    
    name: str
    index: int
    data_type: DataType
    nullable: bool = False
    null_percentage: float = 0.0
    unique_count: int = 0
    total_count: int = 0
    sample_values: List[str] = field(default_factory=list)
    patterns: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    enum_values: Optional[Set[str]] = None
    max_length: int = 0
    min_length: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization.
        
        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        result = asdict(self)
        result['data_type'] = self.data_type.value
        
        # Convert set to sorted list for JSON serialization
        if self.enum_values is not None:
            result['enum_values'] = sorted(list(self.enum_values))
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColumnMetadata':
        """Create ColumnMetadata from dictionary.
        
        Args:
            data: Dictionary containing column metadata.
            
        Returns:
            ColumnMetadata instance.
        """
        # Convert string back to DataType enum
        data['data_type'] = DataType(data['data_type'])
        
        # Convert list back to set for enum_values
        if data.get('enum_values') is not None:
            data['enum_values'] = set(data['enum_values'])
        
        return cls(**data)


@dataclass
class CSVConfiguration:
    """Complete configuration for a CSV file structure.
    
    Attributes:
        source_file: Original CSV file path.
        delimiter: CSV delimiter character.
        quotechar: Quote character used.
        has_header: Whether first row is a header.
        encoding: File encoding detected.
        line_count: Number of data rows (excluding header).
        columns: List of ColumnMetadata for each column.
        analysis_timestamp: When analysis was performed.
        config_version: Version of configuration schema.
        similar_configs: Paths to similar configurations for reuse.
    """
    
    source_file: str
    delimiter: str
    quotechar: str
    has_header: bool
    encoding: str
    line_count: int
    columns: List[ColumnMetadata]
    analysis_timestamp: str = ""
    config_version: str = "1.0"
    similar_configs: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Set analysis timestamp if not provided."""
        if not self.analysis_timestamp:
            self.analysis_timestamp = datetime.now().isoformat()
    
    def save(self, filepath: Union[str, Path]) -> None:
        """Save configuration to JSON file.
        
        Args:
            filepath: Path where configuration should be saved.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = {
            'source_file': self.source_file,
            'delimiter': self.delimiter,
            'quotechar': self.quotechar,
            'has_header': self.has_header,
            'encoding': self.encoding,
            'line_count': self.line_count,
            'analysis_timestamp': self.analysis_timestamp,
            'config_version': self.config_version,
            'similar_configs': self.similar_configs,
            'columns': [col.to_dict() for col in self.columns]
        }
        
        # Helper function to convert sets to lists for JSON serialization
        def convert_sets(obj):
            if isinstance(obj, dict):
                return {k: convert_sets(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_sets(item) for item in obj]
            elif isinstance(obj, set):
                return sorted(list(obj))
            else:
                return obj
        
        config_dict = convert_sets(config_dict)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def load(cls, filepath: Union[str, Path]) -> 'CSVConfiguration':
        """Load configuration from JSON file.
        
        Args:
            filepath: Path to configuration file.
            
        Returns:
            CSVConfiguration instance.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert column dictionaries back to ColumnMetadata objects
        data['columns'] = [ColumnMetadata.from_dict(col) for col in data['columns']]
        
        # Convert enum_values in patterns back to sets if they exist
        for col in data['columns']:
            if 'enum_values' in col.patterns and isinstance(col.patterns['enum_values'], list):
                col.patterns['enum_values'] = set(col.patterns['enum_values'])
        
        return cls(**data)
    
    def get_column(self, name: str) -> Optional[ColumnMetadata]:
        """Get column metadata by name.
        
        Args:
            name: Column name to search for.
            
        Returns:
            ColumnMetadata if found, None otherwise.
        """
        for col in self.columns:
            if col.name == name:
                return col
        return None


class DataTypeDetector:
    """Utility class for detecting data types from string values.
    
    This class provides methods to analyze values and determine the most
    appropriate data type, along with extracting relevant patterns and statistics.
    """
    
    # Common date format patterns
    DATE_PATTERNS = [
        (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),
        (r'^\d{2}/\d{2}/\d{4}$', '%m/%d/%Y'),
        (r'^\d{2}-\d{2}-\d{4}$', '%m-%d-%Y'),
        (r'^\d{4}/\d{2}/\d{2}$', '%Y/%m/%d'),
        (r'^\d{1,2}/\d{1,2}/\d{4}$', '%m/%d/%Y'),
        (r'^\d{4}\d{2}\d{2}$', '%Y%m%d'),
    ]
    
    # Common datetime patterns
    DATETIME_PATTERNS = [
        (r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$', '%Y-%m-%d %H:%M:%S'),
        (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$', '%Y-%m-%dT%H:%M:%S'),
        (r'^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}$', '%m/%d/%Y %H:%M:%S'),
    ]
    
    # Common time patterns
    TIME_PATTERNS = [
        (r'^\d{2}:\d{2}:\d{2}$', '%H:%M:%S'),
        (r'^\d{2}:\d{2}$', '%H:%M'),
        (r'^\d{1,2}:\d{2}\s*[AaPp][Mm]$', '%I:%M %p'),
    ]
    
    # Email pattern
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Phone patterns (various formats)
    PHONE_PATTERNS = [
        r'^\d{3}-\d{3}-\d{4}$',  # 123-456-7890
        r'^\(\d{3}\)\s*\d{3}-\d{4}$',  # (123) 456-7890
        r'^\d{10}$',  # 1234567890
        r'^\+\d{1,3}\s*\d{10}$',  # +1 1234567890
    ]
    
    # URL pattern
    URL_PATTERN = r'^https?://[^\s<>"{}|\\^`\[\]]+$'
    
    @staticmethod
    def is_null(value: str) -> bool:
        """Check if value represents null/empty.
        
        Args:
            value: String value to check.
            
        Returns:
            True if value is null/empty, False otherwise.
        """
        if value is None:
            return True
        
        # Strip and check common null representations
        value_stripped = value.strip()
        return (
            value_stripped == '' or
            value_stripped.lower() in ('null', 'none', 'na', 'n/a', 'nan', '#n/a')
        )
    
    @staticmethod
    def detect_type(values: List[str]) -> Tuple[DataType, Dict[str, Any]]:
        """Detect the most appropriate data type for a list of values.
        
        Analyzes all non-null values and determines the best fitting data type
        along with relevant patterns and statistics.
        
        Args:
            values: List of string values from a column.
            
        Returns:
            Tuple of (detected DataType, dictionary of patterns/metadata).
        """
        # Filter out null values for type detection
        non_null_values = [v for v in values if not DataTypeDetector.is_null(v)]
        
        if not non_null_values:
            return DataType.EMPTY, {}
        
        # Count how many values match each type
        type_matches = {
            DataType.BOOLEAN: 0,
            DataType.INTEGER: 0,
            DataType.FLOAT: 0,
            DataType.DECIMAL: 0,
            DataType.EMAIL: 0,
            DataType.PHONE: 0,
            DataType.URL: 0,
            DataType.DATE: 0,
            DataType.DATETIME: 0,
            DataType.TIME: 0,
        }
        
        patterns: Dict[str, Any] = {}
        
        for value in non_null_values:
            value_stripped = value.strip()
            
            # Check boolean
            if value_stripped.lower() in ('true', 'false', 't', 'f', 'yes', 'no', 'y', 'n', '1', '0'):
                type_matches[DataType.BOOLEAN] += 1
            
            # Check integer
            if DataTypeDetector._is_integer(value_stripped):
                type_matches[DataType.INTEGER] += 1
            
            # Check float
            if DataTypeDetector._is_float(value_stripped):
                type_matches[DataType.FLOAT] += 1
            
            # Check decimal (financial)
            if DataTypeDetector._is_decimal(value_stripped):
                type_matches[DataType.DECIMAL] += 1
            
            # Check email
            if re.match(DataTypeDetector.EMAIL_PATTERN, value_stripped):
                type_matches[DataType.EMAIL] += 1
            
            # Check phone
            if any(re.match(pattern, value_stripped) for pattern in DataTypeDetector.PHONE_PATTERNS):
                type_matches[DataType.PHONE] += 1
            
            # Check URL
            if re.match(DataTypeDetector.URL_PATTERN, value_stripped):
                type_matches[DataType.URL] += 1
            
            # Check datetime (before date)
            datetime_match = DataTypeDetector._check_datetime(value_stripped)
            if datetime_match:
                type_matches[DataType.DATETIME] += 1
                if 'datetime_format' not in patterns:
                    patterns['datetime_format'] = datetime_match
            
            # Check date
            date_match = DataTypeDetector._check_date(value_stripped)
            if date_match:
                type_matches[DataType.DATE] += 1
                if 'date_format' not in patterns:
                    patterns['date_format'] = date_match
            
            # Check time
            time_match = DataTypeDetector._check_time(value_stripped)
            if time_match:
                type_matches[DataType.TIME] += 1
                if 'time_format' not in patterns:
                    patterns['time_format'] = time_match
        
        # Determine the best matching type (requires >80% match for specialized types)
        total_values = len(non_null_values)
        threshold = 0.8
        
        # Check specialized types first
        for data_type in [DataType.EMAIL, DataType.PHONE, DataType.URL, 
                         DataType.DATETIME, DataType.DATE, DataType.TIME, 
                         DataType.BOOLEAN]:
            if type_matches[data_type] / total_values >= threshold:
                if data_type in (DataType.INTEGER, DataType.FLOAT, DataType.DECIMAL):
                    patterns.update(DataTypeDetector._compute_numeric_stats(non_null_values))
                return data_type, patterns
        
        # Check numeric types
        if type_matches[DataType.DECIMAL] / total_values >= threshold:
            patterns.update(DataTypeDetector._compute_numeric_stats(non_null_values))
            return DataType.DECIMAL, patterns
        
        if type_matches[DataType.INTEGER] / total_values >= threshold:
            patterns.update(DataTypeDetector._compute_numeric_stats(non_null_values))
            return DataType.INTEGER, patterns
        
        if type_matches[DataType.FLOAT] / total_values >= threshold:
            patterns.update(DataTypeDetector._compute_numeric_stats(non_null_values))
            return DataType.FLOAT, patterns
        
        # Check if it should be treated as enum (few unique values relative to total)
        unique_values = set(non_null_values)
        if len(unique_values) <= min(20, total_values * 0.5):
            patterns['enum_values'] = unique_values
            return DataType.ENUM, patterns
        
        # Default to string and compute string statistics
        patterns.update(DataTypeDetector._compute_string_stats(non_null_values))
        return DataType.STRING, patterns
    
    @staticmethod
    def _is_integer(value: str) -> bool:
        """Check if value is a valid integer."""
        try:
            # Remove common thousands separators
            clean_value = value.replace(',', '').replace('_', '')
            int(clean_value)
            # Make sure it doesn't contain a decimal point
            return '.' not in value
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def _is_float(value: str) -> bool:
        """Check if value is a valid float."""
        try:
            clean_value = value.replace(',', '').replace('_', '')
            float(clean_value)
            return True
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def _is_decimal(value: str) -> bool:
        """Check if value appears to be a decimal/currency value."""
        try:
            # Remove currency symbols and clean
            clean_value = value.replace('$', '').replace('€', '').replace('£', '')
            clean_value = clean_value.replace(',', '').replace('_', '').strip()
            
            Decimal(clean_value)
            # Typically has exactly 2 decimal places for currency
            return '.' in clean_value
        except:
            return False
    
    @staticmethod
    def _check_date(value: str) -> Optional[str]:
        """Check if value matches a date pattern."""
        for pattern, fmt in DataTypeDetector.DATE_PATTERNS:
            if re.match(pattern, value):
                try:
                    datetime.strptime(value, fmt)
                    return fmt
                except ValueError:
                    continue
        return None
    
    @staticmethod
    def _check_datetime(value: str) -> Optional[str]:
        """Check if value matches a datetime pattern."""
        for pattern, fmt in DataTypeDetector.DATETIME_PATTERNS:
            if re.match(pattern, value):
                try:
                    datetime.strptime(value, fmt)
                    return fmt
                except ValueError:
                    continue
        return None
    
    @staticmethod
    def _check_time(value: str) -> Optional[str]:
        """Check if value matches a time pattern."""
        for pattern, fmt in DataTypeDetector.TIME_PATTERNS:
            if re.match(pattern, value):
                try:
                    datetime.strptime(value, fmt)
                    return fmt
                except ValueError:
                    continue
        return None
    
    @staticmethod
    def _compute_numeric_stats(values: List[str]) -> Dict[str, Any]:
        """Compute statistics for numeric values."""
        numeric_values = []
        
        for value in values:
            try:
                # Clean and convert
                clean_value = value.replace('$', '').replace('€', '').replace('£', '')
                clean_value = clean_value.replace(',', '').replace('_', '').strip()
                numeric_values.append(float(clean_value))
            except:
                continue
        
        if not numeric_values:
            return {}
        
        return {
            'min': min(numeric_values),
            'max': max(numeric_values),
            'mean': statistics.mean(numeric_values),
            'median': statistics.median(numeric_values),
            'stdev': statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0,
        }
    
    @staticmethod
    def _compute_string_stats(values: List[str]) -> Dict[str, Any]:
        """Compute statistics for string values."""
        lengths = [len(v) for v in values]
        
        return {
            'min_length': min(lengths),
            'max_length': max(lengths),
            'avg_length': statistics.mean(lengths),
        }


class CSVAnalyzer:
    """Analyzes CSV files to extract structure and data characteristics.
    
    This class performs comprehensive analysis of CSV files, detecting delimiters,
    data types, patterns, and generating complete configuration metadata that can
    be used for test data generation.
    
    Attributes:
        filepath: Path to the CSV file being analyzed.
        encoding: Detected or specified file encoding.
        sample_size: Number of rows to sample for analysis (None = all rows).
    """
    
    def __init__(
        self,
        filepath: Union[str, Path],
        encoding: str = 'utf-8',
        sample_size: Optional[int] = None
    ) -> None:
        """Initialize CSV analyzer.
        
        Args:
            filepath: Path to CSV file to analyze.
            encoding: File encoding (default: 'utf-8').
            sample_size: Maximum rows to analyze (None for all rows).
        """
        self.filepath = Path(filepath)
        self.encoding = encoding
        self.sample_size = sample_size
        
        if not self.filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {self.filepath}")
    
    def analyze(self) -> CSVConfiguration:
        """Perform complete analysis of the CSV file.
        
        Returns:
            CSVConfiguration containing all detected metadata.
            
        Raises:
            ValueError: If CSV cannot be parsed or is invalid.
        """
        # Detect CSV dialect (delimiter, quotechar, etc.)
        dialect = self._detect_dialect()
        
        # Read and analyze the CSV data
        rows, has_header = self._read_csv(dialect)
        
        if not rows:
            raise ValueError("CSV file is empty or unreadable")
        
        # Extract column data
        num_columns = len(rows[0])
        column_data: List[List[str]] = [[] for _ in range(num_columns)]
        
        for row in rows:
            # Handle rows with different column counts (ragged CSV)
            for i in range(num_columns):
                if i < len(row):
                    column_data[i].append(row[i])
                else:
                    column_data[i].append('')
        
        # Generate column names
        if has_header:
            header_row = rows[0]
            data_rows = rows[1:]
        else:
            header_row = [f"column_{i}" for i in range(num_columns)]
            data_rows = rows
        
        # Analyze each column
        columns = []
        for idx, (col_name, col_values) in enumerate(zip(header_row, column_data)):
            # For columns with headers, skip the header value in data analysis
            analysis_values = col_values[1:] if has_header else col_values
            
            column_metadata = self._analyze_column(
                name=col_name,
                index=idx,
                values=analysis_values
            )
            columns.append(column_metadata)
        
        # Create configuration
        config = CSVConfiguration(
            source_file=str(self.filepath),
            delimiter=dialect.delimiter,
            quotechar=dialect.quotechar,
            has_header=has_header,
            encoding=self.encoding,
            line_count=len(data_rows),
            columns=columns
        )
        
        return config
    
    def _detect_dialect(self) -> csv.Dialect:
        """Detect CSV dialect by reading a sample of the file.
        
        Returns:
            Detected csv.Dialect object.
        """
        with open(self.filepath, 'r', encoding=self.encoding, newline='') as f:
            # Read sample for dialect detection
            sample = f.read(8192)
            
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                return dialect
            except csv.Error:
                # Fall back to default dialect if detection fails
                return csv.excel()
    
    def _read_csv(self, dialect: csv.Dialect) -> Tuple[List[List[str]], bool]:
        """Read CSV file and detect if it has a header.
        
        Args:
            dialect: CSV dialect to use for parsing.
            
        Returns:
            Tuple of (list of rows, has_header boolean).
        """
        rows = []
        
        with open(self.filepath, 'r', encoding=self.encoding, newline='') as f:
            reader = csv.reader(f, dialect=dialect)
            
            for idx, row in enumerate(reader):
                rows.append(row)
                
                # Limit sample size if specified
                if self.sample_size and idx >= self.sample_size:
                    break
        
        # Detect header using csv.Sniffer
        has_header = False
        if len(rows) > 1:
            with open(self.filepath, 'r', encoding=self.encoding, newline='') as f:
                sample = f.read(8192)
                try:
                    sniffer = csv.Sniffer()
                    has_header = sniffer.has_header(sample)
                except csv.Error:
                    # Try heuristic: if first row is all text and subsequent rows have numbers
                    first_row = rows[0]
                    second_row = rows[1] if len(rows) > 1 else []
                    
                    # Check if first row looks like headers (no numbers, mostly text)
                    first_numeric = sum(1 for cell in first_row if DataTypeDetector._is_float(cell))
                    second_numeric = sum(1 for cell in second_row if DataTypeDetector._is_float(cell))
                    
                    has_header = (first_numeric == 0 and second_numeric > 0)
        
        return rows, has_header
    
    def _analyze_column(
        self,
        name: str,
        index: int,
        values: List[str]
    ) -> ColumnMetadata:
        """Analyze a single column's data.
        
        Args:
            name: Column name.
            index: Column index position.
            values: List of all values in the column.
            
        Returns:
            ColumnMetadata with complete analysis results.
        """
        # Count nulls
        null_count = sum(1 for v in values if DataTypeDetector.is_null(v))
        non_null_values = [v for v in values if not DataTypeDetector.is_null(v)]
        
        # Detect data type
        data_type, patterns = DataTypeDetector.detect_type(values)
        
        # Count unique values
        unique_values = set(non_null_values)
        unique_count = len(unique_values)
        
        # Get sample values (up to 10)
        sample_values = list(unique_values)[:10]
        
        # Determine if should be treated as enum
        enum_values = None
        if data_type == DataType.ENUM or (unique_count <= 20 and unique_count < len(non_null_values) * 0.5):
            enum_values = unique_values
            data_type = DataType.ENUM
        
        # Compute string lengths
        string_lengths = [len(str(v)) for v in non_null_values] if non_null_values else [0]
        max_length = max(string_lengths) if string_lengths else 0
        min_length = min(string_lengths) if string_lengths else 0
        
        return ColumnMetadata(
            name=name,
            index=index,
            data_type=data_type,
            nullable=(null_count > 0),
            null_percentage=null_count / len(values) if values else 0.0,
            unique_count=unique_count,
            total_count=len(values),
            sample_values=sample_values,
            patterns=patterns,
            statistics=patterns,  # Statistics are part of patterns dict
            enum_values=enum_values,
            max_length=max_length,
            min_length=min_length
        )


class DataGenerator:
    """Generates synthetic CSV data based on a configuration.
    
    Creates randomized data that matches the structure and characteristics
    defined in a CSVConfiguration, suitable for testing and validation.
    
    Attributes:
        config: CSVConfiguration to use for generation.
        seed: Random seed for reproducible generation (optional).
    """
    
    def __init__(self, config: CSVConfiguration, seed: Optional[int] = None) -> None:
        """Initialize data generator.
        
        Args:
            config: Configuration describing the CSV structure.
            seed: Random seed for reproducibility (default: None).
        """
        self.config = config
        
        if seed is not None:
            random.seed(seed)
    
    def generate_csv(
        self,
        output_path: Union[str, Path],
        num_rows: int,
        include_header: bool = True
    ) -> None:
        """Generate a CSV file with synthetic data.
        
        Args:
            output_path: Path where CSV should be written.
            num_rows: Number of data rows to generate.
            include_header: Whether to include header row (default: True).
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding=self.config.encoding, newline='') as f:
            writer = csv.writer(
                f,
                delimiter=self.config.delimiter,
                quotechar=self.config.quotechar
            )
            
            # Write header if configured
            if include_header and self.config.has_header:
                header = [col.name for col in self.config.columns]
                writer.writerow(header)
            
            # Generate and write data rows
            for _ in range(num_rows):
                row = self._generate_row()
                writer.writerow(row)
    
    def generate_rows(self, num_rows: int) -> List[List[str]]:
        """Generate rows of synthetic data without writing to file.
        
        Args:
            num_rows: Number of rows to generate.
            
        Returns:
            List of rows, where each row is a list of string values.
        """
        rows = []
        
        for _ in range(num_rows):
            rows.append(self._generate_row())
        
        return rows
    
    def _generate_row(self) -> List[str]:
        """Generate a single row of data.
        
        Returns:
            List of string values for each column.
        """
        row = []
        
        for column in self.config.columns:
            # Decide if this value should be null
            if column.nullable and random.random() < column.null_percentage:
                row.append('')
            else:
                value = self._generate_value(column)
                row.append(value)
        
        return row
    
    def _generate_value(self, column: ColumnMetadata) -> str:
        """Generate a single value for a column.
        
        Args:
            column: ColumnMetadata describing the column.
            
        Returns:
            Generated value as a string.
        """
        # Handle enum type - select from known values
        if column.data_type == DataType.ENUM and column.enum_values:
            return random.choice(list(column.enum_values))
        
        # Handle specific data types
        if column.data_type == DataType.INTEGER:
            return self._generate_integer(column)
        
        elif column.data_type == DataType.FLOAT:
            return self._generate_float(column)
        
        elif column.data_type == DataType.DECIMAL:
            return self._generate_decimal(column)
        
        elif column.data_type == DataType.BOOLEAN:
            return random.choice(['True', 'False', 'true', 'false', '1', '0'])
        
        elif column.data_type == DataType.DATE:
            return self._generate_date(column)
        
        elif column.data_type == DataType.DATETIME:
            return self._generate_datetime(column)
        
        elif column.data_type == DataType.TIME:
            return self._generate_time(column)
        
        elif column.data_type == DataType.EMAIL:
            return self._generate_email()
        
        elif column.data_type == DataType.PHONE:
            return self._generate_phone()
        
        elif column.data_type == DataType.URL:
            return self._generate_url()
        
        elif column.data_type == DataType.STRING:
            return self._generate_string(column)
        
        else:  # EMPTY or MIXED
            return ''
    
    def _generate_integer(self, column: ColumnMetadata) -> str:
        """Generate a random integer value."""
        stats = column.statistics
        
        if 'min' in stats and 'max' in stats:
            min_val = int(stats['min'])
            max_val = int(stats['max'])
            
            # Add some variance beyond observed range
            range_size = max_val - min_val
            min_val -= int(range_size * 0.1)
            max_val += int(range_size * 0.1)
            
            return str(random.randint(min_val, max_val))
        else:
            return str(random.randint(1, 1000000))
    
    def _generate_float(self, column: ColumnMetadata) -> str:
        """Generate a random float value."""
        stats = column.statistics
        
        if 'min' in stats and 'max' in stats:
            min_val = float(stats['min'])
            max_val = float(stats['max'])
            
            # Add some variance
            range_size = max_val - min_val
            min_val -= range_size * 0.1
            max_val += range_size * 0.1
            
            value = random.uniform(min_val, max_val)
            return f"{value:.6f}"
        else:
            return f"{random.uniform(0, 1000):.6f}"
    
    def _generate_decimal(self, column: ColumnMetadata) -> str:
        """Generate a random decimal value (typically currency)."""
        stats = column.statistics
        
        if 'min' in stats and 'max' in stats:
            min_val = float(stats['min'])
            max_val = float(stats['max'])
            
            range_size = max_val - min_val
            min_val -= range_size * 0.1
            max_val += range_size * 0.1
            
            value = random.uniform(min_val, max_val)
            return f"{value:.2f}"
        else:
            return f"{random.uniform(0, 10000):.2f}"
    
    def _generate_date(self, column: ColumnMetadata) -> str:
        """Generate a random date value."""
        date_format = column.patterns.get('date_format', '%Y-%m-%d')
        
        # Generate date within the last 10 years
        start_date = datetime.now() - timedelta(days=3650)
        end_date = datetime.now()
        
        time_between = end_date - start_date
        random_days = random.randrange(time_between.days)
        random_date = start_date + timedelta(days=random_days)
        
        return random_date.strftime(date_format)
    
    def _generate_datetime(self, column: ColumnMetadata) -> str:
        """Generate a random datetime value."""
        datetime_format = column.patterns.get('datetime_format', '%Y-%m-%d %H:%M:%S')
        
        # Generate datetime within the last year
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()
        
        time_between = end_date - start_date
        random_seconds = random.randrange(int(time_between.total_seconds()))
        random_datetime = start_date + timedelta(seconds=random_seconds)
        
        return random_datetime.strftime(datetime_format)
    
    def _generate_time(self, column: ColumnMetadata) -> str:
        """Generate a random time value."""
        time_format = column.patterns.get('time_format', '%H:%M:%S')
        
        random_time = datetime.now().replace(
            hour=random.randint(0, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        
        return random_time.strftime(time_format)
    
    def _generate_email(self) -> str:
        """Generate a random email address."""
        username_length = random.randint(5, 12)
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))
        
        domains = ['example.com', 'test.com', 'demo.com', 'sample.org']
        domain = random.choice(domains)
        
        return f"{username}@{domain}"
    
    def _generate_phone(self) -> str:
        """Generate a random phone number."""
        formats = [
            lambda: f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            lambda: f"({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
            lambda: f"{random.randint(1000000000, 9999999999)}",
        ]
        
        return random.choice(formats)()
    
    def _generate_url(self) -> str:
        """Generate a random URL."""
        protocols = ['http', 'https']
        domains = ['example.com', 'test.com', 'demo.org', 'sample.net']
        paths = ['', '/page', '/resource', '/api/v1', '/docs']
        
        protocol = random.choice(protocols)
        domain = random.choice(domains)
        path = random.choice(paths)
        
        return f"{protocol}://{domain}{path}"
    
    def _generate_string(self, column: ColumnMetadata) -> str:
        """Generate a random string value."""
        # Use observed length characteristics
        if column.min_length and column.max_length:
            target_length = random.randint(column.min_length, column.max_length)
        else:
            target_length = random.randint(5, 50)
        
        # Generate words to fill the target length
        words = []
        current_length = 0
        
        while current_length < target_length:
            word_length = random.randint(3, 10)
            word = ''.join(random.choices(string.ascii_letters, k=word_length))
            words.append(word)
            current_length += word_length + 1  # +1 for space
        
        result = ' '.join(words)
        
        # Trim to exact length if needed
        if len(result) > target_length:
            result = result[:target_length].strip()
        
        return result


class ConfigurationComparator:
    """Compare CSV configurations to identify similarities and reuse opportunities.
    
    This class analyzes multiple CSV configurations to find patterns, shared
    structures, and opportunities for test case reuse.
    """
    
    @staticmethod
    def compare_configs(
        config1: CSVConfiguration,
        config2: CSVConfiguration
    ) -> Dict[str, Any]:
        """Compare two configurations and compute similarity metrics.
        
        Args:
            config1: First configuration.
            config2: Second configuration.
            
        Returns:
            Dictionary containing similarity metrics and matching columns.
        """
        # Check basic structure similarity
        same_delimiter = config1.delimiter == config2.delimiter
        same_column_count = len(config1.columns) == len(config2.columns)
        
        # Compare columns
        matching_columns = []
        similar_columns = []
        
        for col1 in config1.columns:
            for col2 in config2.columns:
                if col1.name == col2.name:
                    similarity = ConfigurationComparator._column_similarity(col1, col2)
                    
                    if similarity >= 0.9:
                        matching_columns.append((col1.name, similarity))
                    elif similarity >= 0.7:
                        similar_columns.append((col1.name, col2.name, similarity))
        
        # Compute overall similarity score
        structure_score = 0.0
        if same_delimiter:
            structure_score += 0.2
        if same_column_count:
            structure_score += 0.3
        
        # Column similarity contributes to overall score
        if config1.columns:
            column_match_ratio = len(matching_columns) / len(config1.columns)
            structure_score += 0.5 * column_match_ratio
        
        return {
            'overall_similarity': structure_score,
            'same_delimiter': same_delimiter,
            'same_column_count': same_column_count,
            'matching_columns': matching_columns,
            'similar_columns': similar_columns,
            'can_reuse_tests': structure_score >= 0.7
        }
    
    @staticmethod
    def _column_similarity(col1: ColumnMetadata, col2: ColumnMetadata) -> float:
        """Compute similarity score between two columns.
        
        Args:
            col1: First column metadata.
            col2: Second column metadata.
            
        Returns:
            Similarity score from 0.0 to 1.0.
        """
        score = 0.0
        
        # Same data type
        if col1.data_type == col2.data_type:
            score += 0.4
        
        # Similar nullability
        if col1.nullable == col2.nullable:
            score += 0.2
        
        # Similar null percentage (within 10%)
        if abs(col1.null_percentage - col2.null_percentage) < 0.1:
            score += 0.2
        
        # Similar value diversity
        if col1.total_count > 0 and col2.total_count > 0:
            diversity1 = col1.unique_count / col1.total_count
            diversity2 = col2.unique_count / col2.total_count
            
            if abs(diversity1 - diversity2) < 0.2:
                score += 0.2
        
        return score
    
    @staticmethod
    def find_similar_configs(
        config: CSVConfiguration,
        config_directory: Union[str, Path],
        threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """Find similar configurations in a directory.
        
        Args:
            config: Configuration to compare against.
            config_directory: Directory containing other configuration files.
            threshold: Minimum similarity score (default: 0.7).
            
        Returns:
            List of tuples (config_path, similarity_score) for similar configs.
        """
        config_dir = Path(config_directory)
        
        if not config_dir.exists():
            return []
        
        similar_configs = []
        
        # Search for JSON configuration files
        for config_file in config_dir.glob('*.json'):
            try:
                other_config = CSVConfiguration.load(config_file)
                
                comparison = ConfigurationComparator.compare_configs(config, other_config)
                
                if comparison['overall_similarity'] >= threshold:
                    similar_configs.append((
                        str(config_file),
                        comparison['overall_similarity']
                    ))
            except Exception:
                # Skip files that can't be loaded as configurations
                continue
        
        # Sort by similarity score (descending)
        similar_configs.sort(key=lambda x: x[1], reverse=True)
        
        return similar_configs
