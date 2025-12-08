#!/usr/bin/env python3
"""CSV Generator CLI Tool - Generate test CSV files from configurations.

This command-line tool generates synthetic CSV files based on configuration
files created by the analyzer. The generated CSVs match the structure and
data characteristics of the original files and are suitable for testing.

Usage:
    python generate_test_csv.py config.json -o test_data.csv -n 100
    python generate_test_csv.py config.json --rows 1000 --seed 42
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from lib.csv_analyzer_lib import CSVConfiguration, DataGenerator


def generate_test_csv(
    config_path: str,
    output_path: Optional[str] = None,
    num_rows: int = 100,
    seed: Optional[int] = None,
    no_header: bool = False,
    verbose: bool = False
) -> int:
    """Generate a test CSV file from a configuration.
    
    Args:
        config_path: Path to the configuration JSON file.
        output_path: Path where CSV should be written.
        num_rows: Number of data rows to generate.
        seed: Random seed for reproducibility.
        no_header: Omit header row even if config has one.
        verbose: Print detailed information.
        
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"Error: Configuration file not found: {config_file}", file=sys.stderr)
        return 1
    
    # Determine output path
    if output_path:
        output_file = Path(output_path)
    else:
        output_file = config_file.parent / f"test_{config_file.stem.replace('_config', '')}.csv"
    
    if verbose:
        print(f"Loading configuration from: {config_file}")
        print(f"Output file: {output_file}")
        print(f"Number of rows: {num_rows}")
        if seed is not None:
            print(f"Random seed: {seed}")
        print()
    
    try:
        # Load configuration
        config = CSVConfiguration.load(config_file)
        
        if verbose:
            print("Configuration loaded:")
            print(f"  Source file: {config.source_file}")
            print(f"  Columns: {len(config.columns)}")
            print(f"  Delimiter: {repr(config.delimiter)}")
            print(f"  Has header: {config.has_header}")
            print()
        
        # Create generator
        generator = DataGenerator(config=config, seed=seed)
        
        # Determine whether to include header
        include_header = config.has_header and not no_header
        
        if verbose:
            print("Generating CSV data...")
        
        # Generate CSV file
        generator.generate_csv(
            output_path=output_file,
            num_rows=num_rows,
            include_header=include_header
        )
        
        print(f"Test CSV generated successfully: {output_file}")
        print(f"Rows generated: {num_rows}")
        
        if verbose:
            print()
            print("Column summary:")
            for col in config.columns:
                type_info = col.data_type.value
                if col.enum_values:
                    type_info += f" (enum with {len(col.enum_values)} values)"
                print(f"  {col.name}: {type_info}")
        
        return 0
    
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    except Exception as e:
        print(f"Error generating CSV: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def main() -> int:
    """Main entry point for the CLI tool.
    
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        description='Generate test CSV files from configuration files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 100 rows of test data
  python generate_test_csv.py config.json
  
  # Generate 1000 rows and save to specific file
  python generate_test_csv.py config.json -o test_data.csv -n 1000
  
  # Generate with reproducible random seed
  python generate_test_csv.py config.json --seed 42 --rows 500
  
  # Generate without header row
  python generate_test_csv.py config.json --no-header
        """
    )
    
    parser.add_argument(
        'config_file',
        help='Path to the configuration JSON file'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output CSV file path (default: test_CONFIGNAME.csv)'
    )
    
    parser.add_argument(
        '-n', '--rows',
        type=int,
        default=100,
        help='Number of data rows to generate (default: 100)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducible generation'
    )
    
    parser.add_argument(
        '--no-header',
        action='store_true',
        help='Omit header row even if configuration has one'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print detailed information'
    )
    
    args = parser.parse_args()
    
    return generate_test_csv(
        config_path=args.config_file,
        output_path=args.output,
        num_rows=args.rows,
        seed=args.seed,
        no_header=args.no_header,
        verbose=args.verbose
    )


if __name__ == '__main__':
    sys.exit(main())
