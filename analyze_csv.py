#!/usr/bin/env python3
"""CSV Analyzer CLI Tool - Analyze CSV files and generate configurations.

This command-line tool analyzes CSV files to extract their structure, data types,
and patterns, then generates a configuration file that can be used to create
synthetic test data.

Usage:
    python analyze_csv.py input.csv -o config.json
    python analyze_csv.py input.csv --config-dir ./configs --compare
    python analyze_csv.py input.csv --sample 1000 --encoding utf-8
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from lib.csv_analyzer_lib import (
    CSVAnalyzer,
    CSVConfiguration,
    ConfigurationComparator,
)


def analyze_csv_file(
    input_path: str,
    output_path: Optional[str] = None,
    config_dir: Optional[str] = None,
    compare: bool = False,
    sample_size: Optional[int] = None,
    encoding: str = 'utf-8',
    verbose: bool = False
) -> None:
    """Analyze a CSV file and generate configuration.
    
    Args:
        input_path: Path to the CSV file to analyze.
        output_path: Path where configuration should be saved.
        config_dir: Directory to store/compare configurations.
        compare: Whether to compare with existing configurations.
        sample_size: Maximum number of rows to analyze (None = all).
        encoding: File encoding to use.
        verbose: Whether to print detailed information.
    """
    # Convert paths
    input_file = Path(input_path)
    
    # Determine output path
    if output_path:
        output_file = Path(output_path)
    elif config_dir:
        config_directory = Path(config_dir)
        config_directory.mkdir(parents=True, exist_ok=True)
        output_file = config_directory / f"{input_file.stem}_config.json"
    else:
        output_file = input_file.parent / f"{input_file.stem}_config.json"
    
    if verbose:
        print(f"Analyzing CSV file: {input_file}")
        print(f"Encoding: {encoding}")
        if sample_size:
            print(f"Sample size: {sample_size} rows")
        else:
            print("Analyzing all rows")
        print()
    
    try:
        # Create analyzer and perform analysis
        analyzer = CSVAnalyzer(
            filepath=input_file,
            encoding=encoding,
            sample_size=sample_size
        )
        
        config = analyzer.analyze()
        
        if verbose:
            print("Analysis completed successfully!")
            print(f"  Delimiter: {repr(config.delimiter)}")
            print(f"  Quote character: {repr(config.quotechar)}")
            print(f"  Has header: {config.has_header}")
            print(f"  Number of columns: {len(config.columns)}")
            print(f"  Number of rows: {config.line_count}")
            print()
            
            # Print column information
            print("Column Analysis:")
            print("-" * 80)
            for col in config.columns:
                print(f"  {col.name} (index {col.index}):")
                print(f"    Type: {col.data_type.value}")
                print(f"    Nullable: {col.nullable} ({col.null_percentage:.1%} null)")
                print(f"    Unique values: {col.unique_count} of {col.total_count}")
                
                if col.enum_values:
                    print(f"    Enum values: {sorted(list(col.enum_values))[:5]}...")
                
                if col.statistics:
                    if 'min' in col.statistics:
                        print(f"    Range: [{col.statistics['min']:.2f}, {col.statistics['max']:.2f}]")
                    if 'min_length' in col.statistics:
                        print(f"    Length: [{col.statistics['min_length']}, {col.statistics['max_length']}]")
                
                print()
        
        # Compare with existing configurations if requested
        if compare and config_dir:
            if verbose:
                print("Comparing with existing configurations...")
                print()
            
            similar_configs = ConfigurationComparator.find_similar_configs(
                config=config,
                config_directory=config_dir,
                threshold=0.7
            )
            
            if similar_configs:
                config.similar_configs = [path for path, _ in similar_configs]
                
                if verbose:
                    print(f"Found {len(similar_configs)} similar configuration(s):")
                    for config_path, similarity in similar_configs:
                        print(f"  {Path(config_path).name} (similarity: {similarity:.1%})")
                    print()
                    print("These configurations may share test cases or generation logic.")
                    print()
            else:
                if verbose:
                    print("No similar configurations found.")
                    print()
        
        # Save configuration
        config.save(output_file)
        
        print(f"Configuration saved to: {output_file}")
        
        if config.similar_configs:
            print(f"Similar configs: {len(config.similar_configs)}")
        
        return 0
    
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
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
        description='Analyze CSV files and generate configuration for test data generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  python analyze_csv.py input.csv
  
  # Specify output configuration file
  python analyze_csv.py input.csv -o my_config.json
  
  # Store in config directory and compare with existing configs
  python analyze_csv.py input.csv --config-dir ./configs --compare
  
  # Analyze only first 1000 rows
  python analyze_csv.py input.csv --sample 1000
  
  # Specify encoding for non-UTF8 files
  python analyze_csv.py input.csv --encoding latin-1
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Path to the CSV file to analyze'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output configuration file path (default: INPUT_config.json)'
    )
    
    parser.add_argument(
        '--config-dir',
        help='Directory to store configuration files'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare with existing configurations in config-dir'
    )
    
    parser.add_argument(
        '--sample',
        type=int,
        help='Maximum number of rows to analyze (default: analyze all rows)'
    )
    
    parser.add_argument(
        '--encoding',
        default='utf-8',
        help='File encoding (default: utf-8)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print detailed analysis information'
    )
    
    args = parser.parse_args()
    
    # Call analysis function
    return analyze_csv_file(
        input_path=args.input_file,
        output_path=args.output,
        config_dir=args.config_dir,
        compare=args.compare,
        sample_size=args.sample,
        encoding=args.encoding,
        verbose=args.verbose
    )


if __name__ == '__main__':
    sys.exit(main())
