"""
Examples demonstrating mplog usage in various scenarios
"""

import asyncio
import multiprocessing as mp
import time
import os
from lib.mplog import setup_logging, get_logger


# Example 1: Simple synchronous usage
def example_simple():
    """Basic usage without multiprocessing."""
    print("\n=== Example 1: Simple Logging ===")
    setup_logging(level='INFO', log_file='example1.log')
    
    logger = get_logger(__name__)
    logger.debug("This won't appear (level is INFO)")
    logger.info("This is an info message")
    logger.warning("This is a warning")
    logger.error("This is an error")


# Example 2: Multiprocessing worker
def worker_process(worker_id: int, num_messages: int):
    """Worker function that logs from a separate process."""
    logger = get_logger(f'worker_{worker_id}')
    
    for i in range(num_messages):
        logger.info(f"Worker {worker_id} - Message {i+1}/{num_messages}")
        time.sleep(0.1)
    
    logger.info(f"Worker {worker_id} completed")


def example_multiprocessing():
    """Demonstrate logging from multiple processes."""
    print("\n=== Example 2: Multiprocessing ===")
    setup_logging(level='INFO', log_file='example2.log')
    
    logger = get_logger(__name__)
    logger.info("Starting multiprocessing example")
    
    # Spawn multiple worker processes
    processes = []
    for i in range(4):
        p = mp.Process(target=worker_process, args=(i, 5))
        p.start()
        processes.append(p)
    
    # Wait for all to complete
    for p in processes:
        p.join()
    
    logger.info("All workers completed")


# Example 3: Asyncio usage
async def async_task(task_id: int, duration: float):
    """Async coroutine that logs."""
    logger = get_logger(f'async_task_{task_id}')
    
    logger.info(f"Task {task_id} starting (duration: {duration}s)")
    await asyncio.sleep(duration)
    logger.info(f"Task {task_id} completed")
    
    return f"Result from task {task_id}"


async def async_main():
    """Run multiple async tasks concurrently."""
    logger = get_logger('async_main')
    logger.info("Starting async tasks")
    
    # Create multiple concurrent tasks
    tasks = [
        async_task(i, 0.5 + i * 0.2)
        for i in range(5)
    ]
    
    results = await asyncio.gather(*tasks)
    
    for result in results:
        logger.info(f"Got result: {result}")
    
    logger.info("All async tasks completed")


def example_asyncio():
    """Demonstrate logging with asyncio."""
    print("\n=== Example 3: Asyncio ===")
    setup_logging(level='INFO', log_file='example3.log')
    
    asyncio.run(async_main())


# Example 4: Multiprocessing + Asyncio combined
async def async_worker(worker_id: int, num_tasks: int):
    """Async worker running in a separate process."""
    logger = get_logger(f'mp_async_worker_{worker_id}')
    logger.info(f"Async worker {worker_id} started in process {os.getpid()}")
    
    tasks = [
        async_task(f"{worker_id}_{i}", 0.2)
        for i in range(num_tasks)
    ]
    
    await asyncio.gather(*tasks)
    logger.info(f"Async worker {worker_id} finished")


def run_async_worker(worker_id: int, num_tasks: int):
    """Entry point for process that runs async code."""
    asyncio.run(async_worker(worker_id, num_tasks))


def example_multiprocessing_asyncio():
    """Demonstrate logging with both multiprocessing and asyncio."""
    print("\n=== Example 4: Multiprocessing + Asyncio ===")
    setup_logging(level='INFO', log_file='example4.log')
    
    logger = get_logger(__name__)
    logger.info("Starting combined multiprocessing + asyncio example")
    
    # Spawn processes that each run asyncio event loops
    processes = []
    for i in range(3):
        p = mp.Process(target=run_async_worker, args=(i, 3))
        p.start()
        processes.append(p)
    
    for p in processes:
        p.join()
    
    logger.info("All async workers in all processes completed")


# Example 5: Different log levels and custom formatting
def example_custom_formatting():
    """Demonstrate custom formatting and log levels."""
    print("\n=== Example 5: Custom Formatting ===")
    
    # Custom format with less verbosity
    custom_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    
    setup_logging(
        level='DEBUG',
        log_file='example5.log',
        format_string=custom_format,
        date_format='%H:%M:%S'
    )
    
    logger = get_logger('custom')
    
    logger.debug("Debug message - now visible!")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")


# Example 6: File rotation
def example_file_rotation():
    """Demonstrate log file rotation."""
    print("\n=== Example 6: Log File Rotation ===")
    
    setup_logging(
        level='INFO',
        log_file='example6.log',
        max_bytes=1024,  # Small size to demonstrate rotation
        backup_count=3
    )
    
    logger = get_logger('rotation_test')
    
    # Generate enough logs to trigger rotation
    for i in range(100):
        logger.info(f"Message number {i} - Adding some text to increase size")
    
    logger.info("Check example6.log, example6.log.1, etc. for rotated files")


# Example 7: Exception logging
def example_exception_logging():
    """Demonstrate exception logging."""
    print("\n=== Example 7: Exception Logging ===")
    setup_logging(level='INFO', log_file='example7.log')
    
    logger = get_logger('exceptions')
    
    try:
        result = 1 / 0
    except ZeroDivisionError:
        logger.exception("Caught division by zero - this includes traceback")
    
    logger.info("Program continues after exception")


def main():
    """Run all examples."""
    # Note: These examples will create separate log files
    # In a real application, you'd typically set up logging once
    
    example_simple()
    example_multiprocessing()
    example_asyncio()
    example_multiprocessing_asyncio()
    example_custom_formatting()
    example_file_rotation()
    example_exception_logging()
    
    print("\n=== All examples completed ===")
    print("Check example*.log files for output")


if __name__ == '__main__':
    # Required for multiprocessing on Windows
    mp.freeze_support()
    main()
