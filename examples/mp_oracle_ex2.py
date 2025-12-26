#!/usr/bin/env python3
"""
Oracle Database Maximum Insert Date Query Using Multiprocessing.

This module demonstrates how to use Python's multiprocessing library to
query multiple Oracle database tables in parallel to find the maximum
value of an 'insert_dtm' column in each table.

The example uses:
    - A Manager to share data between processes (Queue and Dictionary)
    - A Queue to distribute table names to worker processes
    - A shared Dictionary to collect results from all workers
    - Logging with process names for debugging and monitoring

Example Usage:
    python oracle_multiprocess_query.py

Requirements:
    - oracledb (or cx_Oracle) package
    - Access to an Oracle database

Author: Training Example
Date: 2024
"""

import logging
import multiprocessing
from multiprocessing import Manager, Process, Queue
from typing import Any
import time
import sys

# Configure logging with process name included in the format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(processName)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a logger for this module
logger = logging.getLogger(__name__)


def get_connection_details(schema_name: str) -> dict[str, str]:
    """
    Retrieve database connection details for the specified schema.

    This is a stub function that should be replaced with actual logic
    to retrieve connection credentials, such as from a configuration file,
    environment variables, or a secrets manager.

    Args:
        schema_name: The name of the Oracle schema to connect to.

    Returns:
        A dictionary containing:
            - 'dsn': The Oracle Data Source Name (host:port/service_name)
            - 'user': The database username
            - 'password': The database password

    Raises:
        ValueError: If the schema_name is empty or None.

    Example:
        >>> details = get_connection_details('MY_SCHEMA')
        >>> print(details['dsn'])
        'localhost:1521/ORCL'
    """
    if not schema_name:
        raise ValueError("Schema name cannot be empty or None")

    logger.debug(f"Retrieving connection details for schema: {schema_name}")

    # STUB: Replace with actual credential retrieval logic
    # This could read from environment variables, a config file,
    # or a secrets management system like AWS Secrets Manager
    return {
        'dsn': 'localhost:1521/ORCL',  # Format: host:port/service_name
        'user': schema_name,
        'password': 'your_password_here'  # NEVER hardcode in production!
    }


def get_database_connection(schema_name: str) -> Any:
    """
    Create and return a database connection for the specified schema.

    This function retrieves connection details and establishes a connection
    to the Oracle database. It uses the oracledb driver (successor to cx_Oracle).

    Args:
        schema_name: The name of the Oracle schema to connect to.

    Returns:
        An Oracle database connection object.

    Raises:
        oracledb.Error: If the database connection fails.

    Note:
        The caller is responsible for closing the connection when done.
    """
    try:
        import oracledb
    except ImportError:
        logger.error("oracledb package not installed. Install with: pip install oracledb")
        raise

    connection_details = get_connection_details(schema_name)

    logger.debug(f"Attempting to connect to DSN: {connection_details['dsn']}")

    connection = oracledb.connect(
        user=connection_details['user'],
        password=connection_details['password'],
        dsn=connection_details['dsn']
    )

    logger.info(f"Successfully connected to database for schema: {schema_name}")
    return connection


def query_max_insert_dtm(table_name: str, schema_name: str) -> tuple[str, Any]:
    """
    Query the maximum insert_dtm value from the specified table.

    This function connects to the database, executes a MAX query on the
    insert_dtm column, and returns the result.

    Args:
        table_name: The name of the table to query.
        schema_name: The schema containing the table.

    Returns:
        A tuple containing:
            - table_name: The name of the queried table
            - max_value: The maximum insert_dtm value, or None if empty/error

    Note:
        Each call creates its own database connection. In production,
        consider using connection pooling for better performance.
    """
    logger.debug(f"Querying max insert_dtm for table: {table_name}")

    try:
        # Get a database connection
        connection = get_database_connection(schema_name)

        try:
            # Create a cursor for executing the query
            cursor = connection.cursor()

            # Build and execute the query
            # Using bind variables would be preferred if table_name came from user input
            query = f"SELECT MAX(insert_dtm) FROM {schema_name}.{table_name}"
            logger.debug(f"Executing query: {query}")

            cursor.execute(query)
            result = cursor.fetchone()

            # Extract the max value from the result tuple
            max_value = result[0] if result else None

            logger.info(f"Table {table_name}: max insert_dtm = {max_value}")
            return (table_name, max_value)

        finally:
            # Always close the cursor and connection
            cursor.close()
            connection.close()
            logger.debug(f"Closed database connection for table: {table_name}")

    except Exception as e:
        logger.error(f"Error querying table {table_name}: {str(e)}")
        return (table_name, f"ERROR: {str(e)}")


def worker_process(
    task_queue: Queue,
    results_dict: dict,
    schema_name: str
) -> None:
    """
    Worker process that consumes table names from a queue and queries each table.

    This function runs in a separate process and continuously pulls table names
    from the shared queue until it receives a sentinel value (None). For each
    table, it queries the maximum insert_dtm value and stores the result in
    the shared results dictionary.

    Args:
        task_queue: A multiprocessing Queue containing table names to process.
                   A None value signals the worker to terminate.
        results_dict: A Manager dictionary to store the query results.
                     Keys are table names, values are max insert_dtm values.
        schema_name: The Oracle schema name containing the tables.

    Returns:
        None. Results are stored in the shared results_dict.

    Note:
        This function is designed to be run as a target for multiprocessing.Process.
        It handles the sentinel pattern for graceful termination.
    """
    process_name = multiprocessing.current_process().name
    logger.info(f"Worker started: {process_name}")

    tables_processed = 0

    while True:
        try:
            # Get the next table name from the queue
            # This will block until an item is available
            table_name = task_queue.get()

            # Check for sentinel value indicating shutdown
            if table_name is None:
                logger.info(
                    f"Worker {process_name} received shutdown signal. "
                    f"Processed {tables_processed} tables."
                )
                break

            logger.debug(f"Worker {process_name} processing table: {table_name}")

            # Query the table and get the result
            table_name, max_value = query_max_insert_dtm(table_name, schema_name)

            # Store the result in the shared dictionary
            results_dict[table_name] = max_value
            tables_processed += 1

            logger.debug(
                f"Worker {process_name} stored result for {table_name}: {max_value}"
            )

        except Exception as e:
            logger.error(
                f"Worker {process_name} encountered an error: {str(e)}",
                exc_info=True
            )

    logger.info(f"Worker {process_name} shutting down gracefully")


def run_parallel_queries(
    table_names: list[str],
    schema_name: str,
    num_workers: int = 12
) -> dict[str, Any]:
    """
    Execute parallel queries to find max insert_dtm for multiple tables.

    This function orchestrates the parallel querying process:
    1. Creates a Manager for shared data structures
    2. Populates a Queue with table names
    3. Spawns worker processes
    4. Waits for all workers to complete
    5. Returns the collected results

    Args:
        table_names: A list of table names to query.
        schema_name: The Oracle schema containing the tables.
        num_workers: Number of worker processes to spawn. Defaults to 12.

    Returns:
        A dictionary mapping table names to their maximum insert_dtm values.
        Tables that encountered errors will have error messages as values.

    Raises:
        ValueError: If table_names is empty or num_workers is less than 1.

    Example:
        >>> tables = ['TABLE1', 'TABLE2', 'TABLE3']
        >>> results = run_parallel_queries(tables, 'MY_SCHEMA', num_workers=4)
        >>> for table, max_dtm in results.items():
        ...     print(f"{table}: {max_dtm}")
    """
    # Validate inputs
    if not table_names:
        raise ValueError("table_names list cannot be empty")
    if num_workers < 1:
        raise ValueError("num_workers must be at least 1")

    logger.info(
        f"Starting parallel query execution for {len(table_names)} tables "
        f"using {num_workers} workers"
    )
    logger.info(f"Schema: {schema_name}")

    # Create a Manager to handle shared data structures
    # The Manager runs in a separate process and provides proxies
    # that can be safely shared between worker processes
    manager = Manager()

    # Create a Queue for distributing table names to workers
    task_queue = manager.Queue()

    # Create a shared dictionary for collecting results
    # This is a proxy object that synchronizes access across processes
    results_dict = manager.dict()

    # Populate the queue with table names
    logger.debug("Populating task queue with table names")
    for table_name in table_names:
        task_queue.put(table_name)
        logger.debug(f"Added table to queue: {table_name}")

    # Add sentinel values (None) to signal workers to shut down
    # We need one sentinel per worker
    logger.debug(f"Adding {num_workers} sentinel values to queue")
    for _ in range(num_workers):
        task_queue.put(None)

    # Create and start worker processes
    workers = []
    logger.info(f"Spawning {num_workers} worker processes")

    for i in range(num_workers):
        # Create a descriptive process name
        process_name = f"Worker-{i+1:02d}"

        # Create the worker process
        worker = Process(
            target=worker_process,
            args=(task_queue, results_dict, schema_name),
            name=process_name
        )

        workers.append(worker)
        worker.start()
        logger.debug(f"Started worker process: {process_name} (PID: {worker.pid})")

    # Wait for all workers to complete
    logger.info("Waiting for all workers to complete...")

    for worker in workers:
        worker.join()
        logger.debug(f"Worker {worker.name} has completed (exit code: {worker.exitcode})")

    logger.info("All worker processes have completed")

    # Convert the Manager dict proxy to a regular dictionary
    # This creates a snapshot of the results
    final_results = dict(results_dict)

    return final_results


def log_results(results: dict[str, Any]) -> None:
    """
    Log the final results from all table queries.

    This function iterates through the results dictionary and logs each
    table's maximum insert_dtm value. It also provides summary statistics.

    Args:
        results: A dictionary mapping table names to max insert_dtm values.

    Returns:
        None. Output is written to the log.
    """
    logger.info("=" * 60)
    logger.info("FINAL RESULTS")
    logger.info("=" * 60)

    # Count successful and failed queries
    successful = 0
    failed = 0

    # Sort results by table name for consistent output
    for table_name in sorted(results.keys()):
        max_value = results[table_name]

        # Check if this was an error result
        if isinstance(max_value, str) and max_value.startswith("ERROR:"):
            logger.warning(f"  {table_name}: {max_value}")
            failed += 1
        else:
            logger.info(f"  {table_name}: {max_value}")
            successful += 1

    # Log summary statistics
    logger.info("-" * 60)
    logger.info(f"Total tables processed: {len(results)}")
    logger.info(f"Successful queries: {successful}")
    logger.info(f"Failed queries: {failed}")
    logger.info("=" * 60)


def main() -> None:
    """
    Main entry point for the Oracle multiprocessing query example.

    This function:
    1. Defines a list of sample table names
    2. Configures the schema and worker count
    3. Executes the parallel queries
    4. Logs the results

    This is designed as a demonstration/training example.
    """
    logger.info("Oracle Multiprocessing Query Example Starting")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Number of CPU cores available: {multiprocessing.cpu_count()}")

    # Configuration
    schema_name = "MY_SCHEMA"
    num_workers = 12  # Default number of worker processes

    # Sample list of table names to query
    # In production, this might come from a database query, config file, or API
    table_names = [
        "CUSTOMERS",
        "ORDERS",
        "ORDER_ITEMS",
        "PRODUCTS",
        "INVENTORY",
        "SUPPLIERS",
        "SHIPMENTS",
        "PAYMENTS",
        "INVOICES",
        "EMPLOYEES",
        "DEPARTMENTS",
        "AUDIT_LOG",
        "USER_SESSIONS",
        "TRANSACTION_HISTORY",
        "NOTIFICATIONS",
    ]

    logger.info(f"Tables to process: {len(table_names)}")
    logger.debug(f"Table list: {table_names}")

    # Record start time for performance measurement
    start_time = time.time()

    try:
        # Execute the parallel queries
        results = run_parallel_queries(
            table_names=table_names,
            schema_name=schema_name,
            num_workers=num_workers
        )

        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        logger.info(f"Total execution time: {elapsed_time:.2f} seconds")

        # Log all results
        log_results(results)

    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        sys.exit(1)

    logger.info("Oracle Multiprocessing Query Example Complete")


if __name__ == "__main__":
    # This guard ensures the code only runs when executed directly,
    # not when imported as a module. This is essential for multiprocessing
    # on Windows, which uses 'spawn' instead of 'fork'.
    main()



"""
This example demonstrates several key concepts for training purposes:

## Key Features

1. **Multiprocessing with Manager**: Uses `Manager()` to create shared data structures (Queue and dict) that can be safely accessed by multiple processes.

2. **Queue-based Task Distribution**: The manager populates a Queue with table names, and workers consume from it until they receive a sentinel value (None).

3. **Sentinel Pattern**: Uses `None` values in the queue to signal workers to shut down gracefully.

4. **Logging with Process Names**: Configures logging to include `%(processName)s` so you can trace which worker performed each action.

5. **Google-style Docstrings**: Complete documentation for all functions including Args, Returns, Raises, and Examples.

6. **Error Handling**: Comprehensive exception handling at multiple levels with appropriate logging.

7. **Stub Function**: `get_connection_details()` is a stub that can be replaced with actual credential retrieval logic.

8. **Best Practices**:
   - Type hints throughout
   - Proper resource cleanup (connections, cursors)
   - Input validation
   - Performance timing
   - Summary statistics

To use this in a real environment, you would:
1. Install `oracledb`: `pip install oracledb`
2. Replace the stub connection details with real values
3. Update the table list with actual table names
"""