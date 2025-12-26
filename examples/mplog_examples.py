#!/usr/bin/env python3
"""
multiprocess_logging_best_practice.py

A complete example demonstrating robust logging in a Python multiprocessing application.

Key Concepts:
1.  **QueueHandler**: Used by worker processes to send raw LogRecords to a shared queue.
    (Workers do not write to files/console directly).
2.  **QueueListener**: Runs in a dedicated thread in the main process. It pulls records
    from the queue and dispatches them to the actual handlers (File, Stream).
3.  **Decoupling**: Formatting and I/O happen only in the main process/listener,
    preventing race conditions and corrupted logs.

Usage:
    python3 multiprocess_logging_best_practice.py
"""

import logging
import logging.handlers
import multiprocessing
import time
import random
import sys
from typing import List


# ---------------------------------------------------------------------------
# Worker Configuration
# ---------------------------------------------------------------------------

def worker_configurer(queue: multiprocessing.Queue) -> None:
    """
    Configures the logger for a worker process.

    Instead of attaching file handlers, we attach a single QueueHandler.
    This sends all log records to the main process via the queue.
    """
    root = logging.getLogger()
    # Avoid duplicate logs if the worker inherits handlers from the parent (POSIX specific)
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    root.setLevel(logging.DEBUG)

    # Just send the record. No formatting happens here to save CPU in the worker.
    queue_handler = logging.handlers.QueueHandler(queue)
    root.addHandler(queue_handler)


def worker_process(queue: multiprocessing.Queue, worker_id: int) -> None:
    """
    Simulates a task running in a separate process.
    """
    worker_configurer(queue)
    logger = logging.getLogger(f"Worker-{worker_id}")

    logger.info("Worker started.")

    # Simulate work
    for i in range(3):
        sleep_time = random.uniform(0.1, 0.5)
        time.sleep(sleep_time)
        logger.debug(f"Processing item {i + 1} (took {sleep_time:.2f}s)")

        # Simulate an occasional warning
        if random.random() < 0.3:
            logger.warning("Random warning encountered during processing.")

    logger.info("Worker finished.")


# ---------------------------------------------------------------------------
# Main / Listener Configuration
# ---------------------------------------------------------------------------

def setup_listener_handlers(log_filename: str) -> List[logging.Handler]:
    """
    Creates the handlers that will actually write the logs (File and Stderr).
    These are passed to the QueueListener, not attached to a logger directly.
    """
    # 1. Define the format for the final output
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(processName)-12s | %(name)-10s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # 2. Console Handler (Stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)  # Example: Only show INFO+ on console

    # 3. File Handler
    file_handler = logging.FileHandler(log_filename, mode='w')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # Example: Capture everything in file

    return [console_handler, file_handler]


def main():
    # 1. Create the shared queue
    queue = multiprocessing.Queue()

    # 2. Setup the Listener
    # The QueueListener accepts the queue and a list of handlers.
    # It automatically starts its own internal thread to watch the queue.
    log_file = "app_debug.log"
    handlers = setup_listener_handlers(log_file)
    listener = logging.handlers.QueueListener(queue, *handlers, respect_handler_level=True)

    print(f"--- Starting Logging Listener (Writing to {log_file}) ---")
    listener.start()

    # 3. Start Worker Processes
    workers = []
    for i in range(1, 4):
        p = multiprocessing.Process(
            target=worker_process,
            args=(queue, i),
            name=f"Process-{i}"
        )
        workers.append(p)
        p.start()

    # 4. Wait for workers to finish
    for p in workers:
        p.join()

    # 5. Clean Shutdown
    # listener.stop() ensures the queue is drained and handlers are closed properly.
    print("--- All workers finished. Stopping listener. ---")
    listener.stop()


if __name__ == "__main__":
    # Necessary for Windows support
    multiprocessing.freeze_support()
    main()
