# !/usr/bin/env python3
"""
Oracle Database Maximum Insert DateTime Query Example.

This module demonstrates the use of Python's multiprocessing library to
concurrently query multiple Oracle database tables for their maximum
'insert_dtm' column values.

The example showcases:
    - multiprocessing.Manager for shared state (Queue and dict)
    - multiprocessing.Process for worker processes
    - Proper logging with process names
    - Oracle database connectivity patterns
    - Clean shutdown with sentinel values

Example Usage:
    python oracle_max_dtm_query.py

Requirements:
    - Python 3.7+
    - oracledb or cx_Oracle package

Author: Training Example
Version: 1.0.0
"""

import logging
import multiprocessing
from multiprocessing import Process, Manager
from multiprocessing.managers import DictProxy
from queue import Empty
from typing import Any, Dict, List, Optional, Tuple
import time
from datetime import datetime


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def configure_logging(level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure and return a logger with process name support.

    Sets up logging to output to stdout with timestamps, log level,
    and the current process name for multiprocessing visibility.

    Args:
        level: The logging level (e.g., logging.DEBUG, logging.INFO).

    Returns:
        A configured Logger instance.

    Example:
        >>> logger = configure_logging(logging.INFO)
        >>> logger.info("Application started")
    """
    # Create a custom format that includes the process name
    log_format = (
        '%(asctime)s - %(levelname)-8s - [%(processName)-12s] - %(message)s'
    )
    date_format = '%Y-%m-%d %H:%M:%S'

    # Configure the root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler()]
    )

    return logging.getLogger(__name__)


# Initialize the module-level logger
logger = configure_logging(logging.DEBUG)


# =============================================================================
# DATABASE CONNECTION FUNCTIONS
# =============================================================================

def get_connection_details(schema_name: str) -> Tuple[str, str, str]:
    """
    Retrieve database connection details for the specified schema.

    This is a stub function that should be replaced with actual
    credential retrieval logic in production environments. Consider
    using:
        - AWS Secrets Manager
        - HashiCorp Vault
        - Environment variables
        - Encrypted configuration files

    Args:
        schema_name: The name of the Oracle schema to connect to.
            This is case-insensitive.

    Returns:
        A tuple containing:
            - dsn (str): Data Source Name (host:port/service_name)
            - user (str): Database username
            - password (str): Database password

    Raises:
        ValueError: If the schema_name is not recognized in the
            configuration map.

    Example:
        >>> dsn, user, password = get_connection_details("MY_SCHEMA")
        >>> print(dsn)
        'localhost:1521/ORCL'

    Warning:
        This stub contains hardcoded credentials for demonstration
        purposes only. Never hardcode credentials in production code!
    """
    logger.debug(f"Retrieving connection details for schema: {schema_name}")

    # ==========================================================================
    # STUB IMPLEMENTATION - REPLACE WITH ACTUAL CREDENTIAL RETRIEVAL
    # ==========================================================================
    # In production, retrieve credentials securely:
    #
    # Option 1: Environment Variables
    #     dsn = os.environ.get('ORACLE_DSN')
    #     user = os.environ.get('ORACLE_USER')
    #     password = os.environ.get('ORACLE_PASSWORD')
    #
    # Option 2: AWS Secrets Manager
    #     import boto3
    #     client = boto3.client('secretsmanager')
    #     secret = client.get_secret_value(SecretId='oracle-credentials')
    #
    # Option 3: Configuration file (with encryption)
    #     from configparser import ConfigParser
    #     config = ConfigParser()
    #     config.read('config.ini')
    # ==========================================================================

    connection_map: Dict[str, Tuple[str, str, str]] = {
        "MY_SCHEMA": (
            "localhost:1521/ORCL",  # DSN: host:port/service_name
            "my_schema_user",  # Username
            "my_secure_password"  # Password
        ),
        "TEST_SCHEMA": (
            "testdb.example.com:1521/TESTDB",
            "test_user",
            "test_password"
        ),
        "PROD_SCHEMA": (
            "proddb.example.com:1521/PRODDB",
            "prod_user",
            "prod_password"
        ),
    }

    # Normalize schema name to uppercase for case-insensitive lookup
    normalized_schema = schema_name.upper()

    if normalized_schema not in connection_map:
        available_schemas = list(connection_map.keys())
        raise ValueError(
            f"Unknown schema: '{schema_name}'. "
            f"Available schemas: {available_schemas}"
        )

    logger.debug(f"Successfully retrieved connection details for {schema_name}")
    return connection_map[normalized_schema]


def create_oracle_connection(dsn: str, user: str, password: str) -> Any:
    """
    Create and return an Oracle database connection.

    This function attempts to create a database connection using the
    newer 'oracledb' driver first, falling back to 'cx_Oracle' if
    oracledb is not available.

    Args:
        dsn: Data Source Name in the format "host:port/service_name".
        user: Database username for authentication.
        password: Database password for authentication.

    Returns:
        An Oracle database connection object that can be used to
        create cursors and execute queries.

    Raises:
        ImportError: If neither oracledb nor cx_Oracle package is installed.
        Exception: If the database connection fails (e.g., invalid
            credentials, network issues, database unavailable).

    Example:
        >>> connection = create_oracle_connection(
        ...     dsn="localhost:1521/ORCL",
        ...     user="myuser",
        ...     password="mypassword"
        ... )
        >>> cursor = connection.cursor()
        >>> cursor.execute("SELECT 1 FROM DUAL")

    Note:
        The connection should be closed when no longer needed to
        release database resources.
    """
    connection = None

    # Try the newer oracledb driver first (recommended by Oracle)
    try:
        import oracledb
        logger.debug("Attempting connection using oracledb driver")

        # oracledb can run in thin mode (no Oracle Client needed)
        # or thick mode (requires Oracle Client libraries)
        connection = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )
        logger.debug("Successfully connected using oracledb driver")
        return connection

    except ImportError:
        logger.debug("oracledb not available, trying cx_Oracle")

    # Fall back to cx_Oracle if oracledb is not installed
    try:
        import cx_Oracle
        logger.debug("Attempting connection using cx_Oracle driver")

        connection = cx_Oracle.connect(
            user=user,
            password=password,
            dsn=dsn
        )
        logger.debug("Successfully connected using cx_Oracle driver")
        return connection

    except ImportError:
        error_message = (
            "No Oracle database driver found. "
            "Please install one of the following:\n"
            "  pip install oracledb    (recommended)\n"
            "  pip install cx_Oracle"
        )
        logger.error(error_message)
        raise ImportError(error_message)


# =============================================================================
# DATABASE QUERY FUNCTIONS
# =============================================================================

def query_max_insert_dtm(
        connection: Any,
        schema_name: str,
        table_name: str
) -> Dict[str, Any]:
    """
    Query a table for its maximum insert_dtm column value.

    Executes a SQL query to find the maximum value of the 'insert_dtm'
    column in the specified table. This is commonly used to determine
    the most recent data insertion time for incremental data processing.

    Args:
        connection: An active Oracle database connection object.
        schema_name: The name of the schema containing the table.
        table_name: The name of the table to query.

    Returns:
        A dictionary containing the query results with the following keys:
            - 'table_name' (str): The name of the table queried
            - 'schema_name' (str): The schema containing the table
            - 'max_insert_dtm' (datetime|None): Maximum insert_dtm value,
                or None if the table is empty or column doesn't exist
            - 'status' (str): 'success' or 'error'
            - 'error' (str|None): Error message if status is 'error'
            - 'query_time' (str): ISO format timestamp of query execution
            - 'row_count' (int): Number of rows returned (0 or 1)

    Example:
        >>> result = query_max_insert_dtm(conn, "MY_SCHEMA", "CUSTOMERS")
        >>> if result['status'] == 'success':
        ...     print(f"Max insert_dtm: {result['max_insert_dtm']}")
        ... else:
        ...     print(f"Error: {result['error']}")

    Note:
        Table and schema names are incorporated directly into the SQL
        query because Oracle does not support bind variables for
        identifiers. Ensure these values are validated to prevent
        SQL injection in production environments.
    """
    process_name = multiprocessing.current_process().name
    query_time = datetime.now().isoformat()

    # Build the result template
    result: Dict[str, Any] = {
        'table_name': table_name,
        'schema_name': schema_name,
        'max_insert_dtm': None,
        'status': 'pending',
        'error': None,
        'query_time': query_time,
        'row_count': 0
    }

    # Construct the SQL query
    # Note: In production, validate schema_name and table_name to prevent
    # SQL injection. Oracle identifiers should match pattern [A-Z][A-Z0-9_$#]*
    sql_query = f"""
        SELECT MAX(insert_dtm) AS max_insert_dtm
        FROM {schema_name}.{table_name}
    """

    logger.debug(f"Executing query: SELECT MAX(insert_dtm) FROM {schema_name}.{table_name}")

    cursor = None
    try:
        # Create cursor and execute the query
        cursor = connection.cursor()
        cursor.execute(sql_query)

        # Fetch the result (should be exactly one row)
        row = cursor.fetchone()

        if row is not None:
            result['max_insert_dtm'] = row[0]
            result['row_count'] = 1

        result['status'] = 'success'
        logger.debug(
            f"Query successful for {table_name}: max_insert_dtm = {result['max_insert_dtm']}"
        )

    except Exception as e:
        # Capture any database errors
        error_message = str(e)
        result['status'] = 'error'
        result['error'] = error_message
        logger.error(f"Query failed for {schema_name}.{table_name}: {error_message}")

    finally:
        # Always close the cursor to release resources
        if cursor is not None:
            try:
                cursor.close()
            except Exception as close_error:
                logger.warning(f"Error closing cursor: {close_error}")

    return result


# =============================================================================
# WORKER PROCESS FUNCTION
# =============================================================================

def worker_process(
        task_queue: multiprocessing.Queue,
        results_dict: DictProxy,
        schema_name: str,
        dsn: str,
        user: str,
        password: str
) -> None:
    """
    Worker process that queries tables for maximum insert_dtm values.

    This function runs in a separate process and performs the following:
        1. Establishes its own database connection
        2. Continuously retrieves table names from the shared task queue
        3. Queries each table for its maximum insert_dtm value
        4. Stores results in the shared results dictionary
        5. Shuts down gracefully when receiving a None sentinel value

    Each worker maintains its own database connection to avoid
    connection sharing issues across process boundaries.

    Args:
        task_queue: A multiprocessing Queue containing table names to
            process. Workers expect None as a sentinel value to signal
            shutdown.
        results_dict: A Manager-created shared dictionary for storing
            query results. Keys are table names, values are result dicts.
        schema_name: The Oracle schema containing the tables to query.
        dsn: Data Source Name for establishing database connection.
        user: Database username for authentication.
        password: Database password for authentication.

    Note:
        This function is designed to be used as the target for a
        multiprocessing.Process. It handles its own exceptions and
        ensures proper cleanup of database resources.

    Example:
        >>> # This function is typically not called directly
        >>> # It's used as a Process target:
        >>> worker = Process(
        ...     target=worker_process,
        ...     args=(queue, results, schema, dsn, user, password)
        ... )
        >>> worker.start()
    """
    process_name = multiprocessing.current_process().name
    logger.info(f"Worker process starting up")

    connection = None
    tables_processed = 0
    tables_succeeded = 0
    tables_failed = 0

    try:
        # =====================================================================
        # ESTABLISH DATABASE CONNECTION
        # =====================================================================
        # Each worker creates its own connection because database connections
        # cannot be safely shared across process boundaries
        logger.debug(f"Establishing database connection to {dsn}")
        connection = create_oracle_connection(dsn, user, password)
        logger.info(f"Database connection established successfully")

        # =====================================================================
        # MAIN PROCESSING LOOP
        # =====================================================================
        # Process tables until we receive the shutdown sentinel (None)
        while True:
            table_name: Optional[str] = None

            try:
                # Get the next table from the queue with a timeout
                # The timeout allows us to periodically check for issues
                # and prevents indefinite blocking
                table_name = task_queue.get(timeout=5.0)

            except Empty:
                # Queue is temporarily empty, continue waiting
                logger.debug(f"Queue empty, waiting for more tasks...")
                continue

            except Exception as queue_error:
                logger.error(f"Error getting task from queue: {queue_error}")
                continue

            # Check for the shutdown sentinel value
            if table_name is None:
                logger.debug(f"Received shutdown sentinel, exiting loop")
                break

            # Process the table
            logger.info(f"Processing table: {table_name}")

            try:
                # Execute the query for this table
                result = query_max_insert_dtm(
                    connection=connection,
                    schema_name=schema_name,
                    table_name=table_name
                )

                # Store the result in the shared dictionary
                results_dict[table_name] = result
                tables_processed += 1

                # Track success/failure counts
                if result['status'] == 'success':
                    tables_succeeded += 1
                    logger.info(
                        f"Completed {table_name}: "
                        f"max_insert_dtm = {result['max_insert_dtm']}"
                    )
                else:
                    tables_failed += 1
                    logger.warning(
                        f"Failed {table_name}: {result.get('error', 'Unknown error')}"
                    )

                # Log detailed result at DEBUG level
                logger.debug(f"Full result for {table_name}: {result}")

            except Exception as processing_error:
                # Handle unexpected errors during table processing
                tables_processed += 1
                tables_failed += 1

                error_result = {
                    'table_name': table_name,
                    'schema_name': schema_name,
                    'max_insert_dtm': None,
                    'status': 'error',
                    'error': str(processing_error),
                    'query_time': datetime.now().isoformat(),
                    'row_count': 0
                }
                results_dict[table_name] = error_result
                logger.error(f"Unexpected error processing {table_name}: {processing_error}")

    except Exception as worker_error:
        # Handle critical errors that prevent the worker from functioning
        logger.error(f"Critical worker error: {worker_error}")

    finally:
        # =====================================================================
        # CLEANUP
        # =====================================================================
        # Ensure database connection is properly closed
        if connection is not None:
            try:
                connection.close()
                logger.debug(f"Database connection closed successfully")
            except Exception as close_error:
                logger.warning(f"Error closing database connection: {close_error}")

        # Log worker statistics
        logger.info(
            f"Worker shutting down - "
            f"Processed: {tables_processed}, "
            f"Succeeded: {tables_succeeded}, "
            f"Failed: {tables_failed}"
        )


# =============================================================================
# MAIN ORCHESTRATION FUNCTION
# =============================================================================

def process_tables(
        schema_name: str,
        table_names: List[str],
        num_workers: int = 12
) -> Dict[str, Dict[str, Any]]:
    """
    Process multiple tables concurrently to find maximum insert_dtm values.

    This function orchestrates the parallel processing of multiple Oracle
    database tables using a pool of worker processes. It implements the
    producer-consumer pattern with a shared queue for work distribution
    and a shared dictionary for result collection.

    Architecture:
        1. A Manager creates process-safe shared data structures
        2. The main process (producer) populates the task queue
        3. Worker processes (consumers) query tables and store results
        4. Sentinel values (None) signal workers to shut down
        5. Results are collected and returned after all workers complete

    Args:
        schema_name: The Oracle schema containing the tables to query.
            Must be a valid schema name recognized by get_connection_details().
        table_names: A list of table names to query for max insert_dtm.
            Each table must exist in the specified schema and have an
            'insert_dtm' column.
        num_workers: Number of worker processes to spawn. Defaults to 12.
            Consider setting this based on:
            - Number of CPU cores available
            - Database connection pool limits
            - Expected query execution time

    Returns:
        A dictionary mapping table names to their query results.
        Each value is a dictionary containing:
            - 'max_insert_dtm': The maximum datetime value or None
            - 'status': 'success' or 'error'
            - 'error': Error message if applicable
            - Other metadata fields

    Raises:
        ValueError: If table_names is empty or schema_name is empty/None.

    Example:
        >>> tables = ["CUSTOMERS", "ORDERS", "PRODUCTS"]
        >>> results = process_tables(
        ...     schema_name="MY_SCHEMA",
        ...     table_names=tables,
        ...     num_workers=4
        ... )
        >>> for table, result in results.items():
        ...     if result['status'] == 'success':
        ...         print(f"{table}: {result['max_insert_dtm']}")

    Note:
        The number of workers should not exceed the number of tables,
        as excess workers will immediately receive shutdown signals.
    """
    # =========================================================================
    # INPUT VALIDATION
    # =========================================================================
    if not table_names:
        raise ValueError("table_names list cannot be empty")

    if not schema_name or not schema_name.strip():
        raise ValueError("schema_name is required and cannot be empty")

    # Adjust worker count if we have fewer tables than workers
    effective_workers = min(num_workers, len(table_names))
    if effective_workers < num_workers:
        logger.info(
            f"Reducing worker count from {num_workers} to {effective_workers} "
            f"(only {len(table_names)} tables to process)"
        )

    logger.info(f"Starting parallel table processing")
    logger.info(f"  Schema: {schema_name}")
    logger.info(f"  Tables to process: {len(table_names)}")
    logger.info(f"  Worker processes: {effective_workers}")
    logger.debug(f"  Table list: {table_names}")

    # =========================================================================
    # GET DATABASE CONNECTION DETAILS
    # =========================================================================
    dsn, user, password = get_connection_details(schema_name)
    logger.debug(f"Retrieved connection details for schema '{schema_name}'")

    # =========================================================================
    # CREATE MANAGER AND SHARED DATA STRUCTURES
    # =========================================================================
    # The Manager provides a way to create data that can be shared between
    # processes. It runs a server process that holds the actual data, and
    # provides proxy objects for other processes to access it.

    with Manager() as manager:
        # Create a process-safe Queue for distributing work
        # Workers will pull table names from this queue
        task_queue: multiprocessing.Queue = manager.Queue()

        # Create a process-safe dictionary for collecting results
        # Workers will store their query results here
        results_dict: DictProxy = manager.dict()

        # =====================================================================
        # POPULATE THE TASK QUEUE
        # =====================================================================
        logger.info("Populating task queue with table names")
        for table_name in table_names:
            task_queue.put(table_name)
            logger.debug(f"  Added to queue: {table_name}")

        # Add sentinel values (None) to signal workers to shut down
        # We need one sentinel per worker to ensure all workers receive
        # the shutdown signal
        logger.debug(f"Adding {effective_workers} shutdown sentinels to queue")
        for _ in range(effective_workers):
            task_queue.put(None)

        logger.info(
            f"Task queue populated: {len(table_names)} tables + "
            f"{effective_workers} sentinels"
        )

        # =====================================================================
        # CREATE AND START WORKER PROCESSES
        # =====================================================================
        workers: List[Process] = []

        logger.info(f"Spawning {effective_workers} worker processes")
        for worker_id in range(effective_workers):
            # Create a worker process with a descriptive name
            worker = Process(
                target=worker_process,
                name=f"Worker-{worker_id + 1:02d}",  # e.g., "Worker-01"
                args=(
                    task_queue,
                    results_dict,
                    schema_name,
                    dsn,
                    user,
                    password
                )
            )
            workers.append(worker)

            # Start the worker process
            worker.start()
            logger.debug(
                f"Started {worker.name} (PID: {worker.pid})"
            )

        logger.info(f"All {effective_workers} worker processes started")

        # =====================================================================
        # WAIT FOR ALL WORKERS TO COMPLETE
        # =====================================================================
        logger.info("Waiting for all workers to complete...")

        for worker in workers:
            # join() blocks until the worker process terminates
            worker.join()

            # Log the worker completion status
            exit_code = worker.exitcode
            if exit_code == 0:
                logger.debug(f"{worker.name} completed successfully (exit code: 0)")
            else:
                logger.warning(
                    f"{worker.name} completed with exit code: {exit_code}"
                )

        logger.info("All worker processes have completed")

        # =====================================================================
        # EXTRACT RESULTS FROM SHARED DICTIONARY
        # =====================================================================
        # Convert the Manager's DictProxy to a regular dict before exiting
        # the Manager context. The proxy won't be accessible after the
        # Manager shuts down.
        final_results: Dict[str, Dict[str, Any]] = dict(results_dict)

        logger.debug(f"Extracted {len(final_results)} results from shared dictionary")

    # Manager context has ended - shared resources are cleaned up

    return final_results


# =============================================================================
# RESULTS LOGGING FUNCTION
# =============================================================================

def log_results(results: Dict[str, Dict[str, Any]]) -> None:
    """
    Log the final results from all table queries in a formatted manner.

    This function provides a comprehensive summary of the processing
    results, including:
        - Total counts (processed, successful, failed)
        - Individual table results sorted alphabetically
        - Detailed metadata at DEBUG level

    Args:
        results: Dictionary mapping table names to their query results.
            Each result should contain 'status', 'max_insert_dtm', and
            optionally 'error' keys.

    Example:
        >>> results = {
        ...     'CUSTOMERS': {'status': 'success', 'max_insert_dtm': datetime(2024, 1, 15)},
        ...     'ORDERS': {'status': 'error', 'error': 'Table not found'}
        ... }
        >>> log_results(results)
        # Outputs formatted summary to log

    Note:
        This function uses INFO level for summary information and
        individual results, and DEBUG level for detailed metadata.
    """
    # Header
    logger.info("=" * 70)
    logger.info("PROCESSING RESULTS SUMMARY")
    logger.info("=" * 70)

    # Calculate summary statistics
    total_count = len(results)
    success_count = sum(
        1 for result in results.values()
        if result.get('status') == 'success'
    )
    error_count = sum(
        1 for result in results.values()
        if result.get('status') == 'error'
    )

    # Log summary statistics
    logger.info(f"Total tables processed:  {total_count}")
    logger.info(f"Successful queries:      {success_count}")
    logger.info(f"Failed queries:          {error_count}")

    if total_count > 0:
        success_rate = (success_count / total_count) * 100
        logger.info(f"Success rate:            {success_rate:.1f}%")

    logger.info("-" * 70)

    # Log individual results, sorted by table name for consistency
    logger.info("Individual Table Results:")
    logger.info("-" * 70)

    for table_name in sorted(results.keys()):
        result = results[table_name]
        status = result.get('status', 'unknown')
        max_dtm = result.get('max_insert_dtm')

        if status == 'success':
            # Format the datetime value for display
            if max_dtm is not None:
                if hasattr(max_dtm, 'strftime'):
                    dtm_str = max_dtm.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    dtm_str = str(max_dtm)
            else:
                dtm_str = "NULL (table may be empty)"

            logger.info(f"  {table_name:30} | SUCCESS | {dtm_str}")
        else:
            error_msg = result.get('error', 'Unknown error')
            # Truncate long error messages for readability
            if len(error_msg) > 40:
                error_msg = error_msg[:37] + "..."
            logger.info(f"  {table_name:30} | ERROR   | {error_msg}")

        # Log full details at DEBUG level
        logger.debug(f"  Full result for {table_name}: {result}")

    logger.info("-" * 70)

    # Log any tables that were in the queue but have no results
    # (this shouldn't happen in normal operation)
    if error_count > 0:
        logger.info("Tables with errors:")
        for table_name in sorted(results.keys()):
            result = results[table_name]
            if result.get('status') == 'error':
                logger.info(f"  - {table_name}: {result.get('error')}")

    logger.info("=" * 70)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> None:
    """
    Main entry point for the Oracle max insert_dtm query example.

    This function demonstrates the complete workflow of using
    multiprocessing to query multiple Oracle database tables
    concurrently. The workflow includes:

        1. Defining configuration (schema, tables, worker count)
        2. Invoking the parallel processing function
        3. Logging and displaying the results
        4. Measuring and reporting execution time

    The function uses sensible defaults and provides comprehensive
    logging throughout the process.

    Example:
        >>> # Run directly
        >>> main()

        >>> # Or from command line
        >>> python oracle_max_dtm_query.py

    Note:
        This example uses a stub connection function. In production,
        replace get_connection_details() with actual credential
        retrieval logic.
    """
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    # These values would typically come from command-line arguments,
    # environment variables, or configuration files

    schema_name = "MY_SCHEMA"
    num_workers = 12  # Default number of worker processes

    # List of tables to query for maximum insert_dtm
    # In production, this might come from:
    #   - A configuration file
    #   - A database metadata query
    #   - Command-line arguments
    #   - An API call
    table_names = [
        "CUSTOMERS",
        "CUSTOMER_ADDRESSES",
        "ORDERS",
        "ORDER_ITEMS",
        "ORDER_STATUS_HISTORY",
        "PRODUCTS",
        "PRODUCT_CATEGORIES",
        "PRODUCT_INVENTORY",
        "SUPPLIERS",
        "SUPPLIER_CONTACTS",
        "EMPLOYEES",
        "EMPLOYEE_DEPARTMENTS",
        "DEPARTMENTS",
        "INVOICES",
        "INVOICE_LINE_ITEMS",
        "PAYMENTS",
        "PAYMENT_METHODS",
        "SHIPMENTS",
        "SHIPMENT_TRACKING",
        "AUDIT_LOG",
        "USER_SESSIONS",
        "USER_ACTIVITY_LOG",
        "SYSTEM_EVENTS",
        "CONFIGURATION_HISTORY",
    ]

    # =========================================================================
    # STARTUP LOGGING
    # =========================================================================
    logger.info("=" * 70)
    logger.info("ORACLE MAX INSERT_DTM QUERY TOOL")
    logger.info("=" * 70)
    logger.info(f"Schema:           {schema_name}")
    logger.info(f"Number of tables: {len(table_names)}")
    logger.info(f"Worker processes: {num_workers}")
    logger.info("=" * 70)

    # Record start time for performance measurement
    start_time = time.time()

    # =========================================================================
    # MAIN PROCESSING
    # =========================================================================
    try:
        # Process all tables using parallel workers
        results = process_tables(
            schema_name=schema_name,
            table_names=table_names,
            num_workers=num_workers
        )

        # Log all results
        log_results(results)

        # Check for any missing results (tables that weren't processed)
        missing_tables = set(table_names) - set(results.keys())
        if missing_tables:
            logger.warning(
                f"The following tables were not processed: {missing_tables}"
            )

    except ValueError as validation_error:
        logger.error(f"Validation error: {validation_error}")
        raise

    except Exception as unexpected_error:
        logger.error(f"Unexpected error during processing: {unexpected_error}")
        raise

    finally:
        # =====================================================================
        # CLEANUP AND FINAL REPORTING
        # =====================================================================
        # Calculate and log total execution time
        elapsed_time = time.time() - start_time

        logger.info("=" * 70)
        logger.info(f"Total execution time: {elapsed_time:.2f} seconds")

        if len(table_names) > 0:
            avg_time_per_table = elapsed_time / len(table_names)
            logger.info(f"Average time per table: {avg_time_per_table:.3f} seconds")

        logger.info("ORACLE MAX INSERT_DTM QUERY TOOL - COMPLETE")
        logger.info("=" * 70)


# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Use the spawn method for creating new processes
    # This is the default on Windows and more portable across platforms
    # It also avoids potential issues with forking and certain libraries
    multiprocessing.set_start_method('spawn', force=True)

    # Run the main function
    main()

"""
## Key Features of This Example

### 1. **Multiprocessing Architecture**
- Uses
`Manager`
to
create
shared
`Queue`(
for task distribution) and `dict` ( for results)
- Implements
producer - consumer
pattern
with sentinel values for clean shutdown
- Each
worker
maintains
its
own
database
connection(connections
can
't be shared across processes)

### 2. **Logging**
- Includes
process
name in all
log
messages
via
` % (processName)
s
`
- Uses
INFO
for progress updates and DEBUG for detailed information
- Comprehensive result logging at the end

### 3. **Documentation**
- Complete Google-style docstrings for all functions
- Detailed comments explaining the "why" behind design decisions
- Examples in docstrings where applicable

### 4. **Best Practices**
- Type hints throughout
- Proper exception handling with specific error messages
- Resource cleanup in `finally` blocks
- Input
validation
- Configurable
worker
count
with sensible defaults

### 5. **Safety Features**
- Graceful
shutdown
using
sentinel
values
- Timeout
on
queue
operations
to
prevent
deadlocks
- Proper
connection
lifecycle
management
"""