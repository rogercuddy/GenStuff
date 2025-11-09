"""
Simple test to verify mplog works correctly
"""

import asyncio
import multiprocessing as mp
import time
from lib.mplog import setup_logging, get_logger


def worker_function(worker_id: int):
    """Simple worker that logs a few messages."""
    logger = get_logger(f'worker_{worker_id}')
    logger.info(f"Worker {worker_id} started")
    time.sleep(0.5)
    logger.info(f"Worker {worker_id} finished")


async def async_function(task_id: int):
    """Simple async function that logs."""
    logger = get_logger(f'async_task_{task_id}')
    logger.info(f"Async task {task_id} starting")
    await asyncio.sleep(0.3)
    logger.info(f"Async task {task_id} completed")


def test_basic_logging():
    """Test basic logging functionality."""
    print("Testing basic logging...")
    setup_logging(level='INFO', log_file='test_basic.log')
    
    logger = get_logger('test_basic')
    logger.info("Basic logging test - info")
    logger.warning("Basic logging test - warning")
    logger.error("Basic logging test - error")
    
    print("✓ Basic logging test passed")


def test_multiprocessing():
    """Test multiprocessing logging."""
    print("\nTesting multiprocessing logging...")
    setup_logging(level='INFO', log_file='test_multiprocessing.log')
    
    logger = get_logger('test_mp')
    logger.info("Starting multiprocessing test")
    
    # Create 3 worker processes
    processes = []
    for i in range(3):
        p = mp.Process(target=worker_function, args=(i,))
        p.start()
        processes.append(p)
    
    # Wait for all to finish
    for p in processes:
        p.join()
    
    logger.info("Multiprocessing test completed")
    print("✓ Multiprocessing logging test passed")


def test_asyncio():
    """Test asyncio logging."""
    print("\nTesting asyncio logging...")
    setup_logging(level='INFO', log_file='test_asyncio.log')
    
    async def run_test():
        logger = get_logger('test_async')
        logger.info("Starting asyncio test")
        
        # Create 3 concurrent tasks
        tasks = [async_function(i) for i in range(3)]
        await asyncio.gather(*tasks)
        
        logger.info("Asyncio test completed")
    
    asyncio.run(run_test())
    print("✓ Asyncio logging test passed")


# This function was previously defined inside test_combined
async def combined_worker(worker_id):
    """Worker coroutine for combined test."""
    logger = get_logger(f'combined_worker_{worker_id}')
    logger.info(f"Combined worker {worker_id} started")
    
    tasks = [async_function(f"{worker_id}_{i}") for i in range(2)]
    await asyncio.gather(*tasks)
    
    logger.info(f"Combined worker {worker_id} finished")


# This function was previously defined inside test_combined
def run_async_worker(worker_id):
    """Entry point for process running async code."""
    asyncio.run(combined_worker(worker_id))


def test_combined():
    """Test combined multiprocessing + asyncio."""
    print("\nTesting combined multiprocessing + asyncio...")
    setup_logging(level='INFO', log_file='test_combined.log')
    
    logger = get_logger('test_combined')
    logger.info("Starting combined test")
    
    # Create 2 processes, each running async tasks
    processes = []
    for i in range(2):
        p = mp.Process(target=run_async_worker, args=(i,))
        p.start()
        processes.append(p)
    
    for p in processes:
        p.join()
    
    logger.info("Combined test completed")
    print("✓ Combined multiprocessing + asyncio test passed")


def main():
    """Run all tests."""
    print("=" * 50)
    print("Running mplog tests")
    print("=" * 50)
    
    test_basic_logging()
    test_multiprocessing()
    test_asyncio()
    test_combined()
    
    print("\n" + "=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)
    print("\nCheck test_*.log files for output")


if __name__ == '__main__':
    mp.freeze_support()
    main()
