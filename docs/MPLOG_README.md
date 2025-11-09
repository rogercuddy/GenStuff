# mplog - Multiprocessing & Asyncio Logging Library

A simple, robust Python logging library that handles the complexity of logging in programs that use multiprocessing and/or asyncio.

## Why mplog?

Standard Python logging can have issues in multiprocessing contexts:
- File handle conflicts when multiple processes write to the same file
- Race conditions and garbled log messages
- Complex setup required with QueueHandler/QueueListener

**mplog** handles all of this complexity for you with a simple API.

## Features

- ✅ **Multiprocessing-safe**: Uses queue-based logging under the hood
- ✅ **Asyncio-compatible**: Works seamlessly with async/await code
- ✅ **Simple API**: Just call `setup_logging()` once and use `get_logger()` everywhere
- ✅ **Stderr and file output**: Log to console, file, or both
- ✅ **Log rotation**: Automatic log file rotation with configurable size limits
- ✅ **Process/thread info**: Includes process and thread information in log messages
- ✅ **Zero configuration required**: Works out of the box with sensible defaults

## Installation

Simply copy `mplog.py` to your project directory and import it.

```python
from mplog import setup_logging, get_logger
```

## Quick Start

```python
from mplog import setup_logging, get_logger
import multiprocessing as mp

def worker():
    logger = get_logger(__name__)
    logger.info("Hello from worker process!")

if __name__ == '__main__':
    # Set up logging once in the main process
    setup_logging(level='INFO', log_file='app.log')
    
    # Use logger in main process
    logger = get_logger(__name__)
    logger.info("Starting application")
    
    # Spawn worker processes - they'll use the same logging setup
    p = mp.Process(target=worker)
    p.start()
    p.join()
    
    logger.info("Application finished")
```

## API Reference

### `setup_logging()`

Set up the logging system. Call this once in your main process before spawning workers.

**Parameters:**
- `level` (int/str, default='INFO'): Logging level (e.g., 'DEBUG', 'INFO', logging.WARNING)
- `log_file` (str/Path, optional): Path to log file. If None, only logs to stderr
- `log_to_stderr` (bool, default=True): Whether to log to stderr
- `format_string` (str, optional): Custom format string for log messages
- `date_format` (str, optional): Custom date format string
- `file_mode` (str, default='a'): File mode ('a' for append, 'w' for write)
- `file_encoding` (str, default='utf-8'): Encoding for log file
- `max_bytes` (int, default=10MB): Maximum log file size before rotation (0 to disable)
- `backup_count` (int, default=5): Number of backup files to keep

**Example:**
```python
setup_logging(
    level='DEBUG',
    log_file='app.log',
    max_bytes=5 * 1024 * 1024,  # 5MB
    backup_count=3
)
```

### `get_logger(name=None)`

Get a logger instance that works safely with multiprocessing and asyncio.

**Parameters:**
- `name` (str, optional): Logger name (typically `__name__`)

**Returns:** `logging.Logger` instance

**Example:**
```python
logger = get_logger(__name__)
logger.info("This is safe in any process or coroutine!")
```

### `shutdown_logging()`

Gracefully shut down the logging system. Automatically called on exit, but can be called manually.

### `is_logging_setup()`

Check if logging has been set up.

**Returns:** `bool`

## Usage Examples

### Basic Usage

```python
from mplog import setup_logging, get_logger

setup_logging(level='INFO', log_file='app.log')
logger = get_logger(__name__)

logger.info("This is an info message")
logger.error("This is an error")
```

### Multiprocessing

```python
import multiprocessing as mp
from mplog import setup_logging, get_logger

def worker(worker_id):
    logger = get_logger(f'worker_{worker_id}')
    logger.info(f"Worker {worker_id} started")
    # Do work...
    logger.info(f"Worker {worker_id} finished")

if __name__ == '__main__':
    setup_logging(level='INFO', log_file='workers.log')
    
    processes = [mp.Process(target=worker, args=(i,)) for i in range(4)]
    for p in processes:
        p.start()
    for p in processes:
        p.join()
```

### Asyncio

```python
import asyncio
from mplog import setup_logging, get_logger

async def async_task(task_id):
    logger = get_logger(f'task_{task_id}')
    logger.info(f"Task {task_id} starting")
    await asyncio.sleep(1)
    logger.info(f"Task {task_id} completed")

async def main():
    tasks = [async_task(i) for i in range(5)]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    setup_logging(level='INFO', log_file='async.log')
    asyncio.run(main())
```

### Multiprocessing + Asyncio

```python
import asyncio
import multiprocessing as mp
from mplog import setup_logging, get_logger

async def async_worker(worker_id):
    logger = get_logger(f'async_worker_{worker_id}')
    logger.info(f"Async worker {worker_id} started")
    await asyncio.sleep(1)
    logger.info(f"Async worker {worker_id} finished")

def run_async_worker(worker_id):
    asyncio.run(async_worker(worker_id))

if __name__ == '__main__':
    setup_logging(level='INFO', log_file='combined.log')
    
    # Each process runs its own asyncio event loop
    processes = [mp.Process(target=run_async_worker, args=(i,)) for i in range(3)]
    for p in processes:
        p.start()
    for p in processes:
        p.join()
```

### Custom Formatting

```python
from mplog import setup_logging, get_logger

setup_logging(
    level='DEBUG',
    log_file='custom.log',
    format_string='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    date_format='%H:%M:%S'
)

logger = get_logger('custom')
logger.debug("This uses custom formatting")
```

### Exception Logging

```python
from mplog import setup_logging, get_logger

setup_logging(level='INFO', log_file='errors.log')
logger = get_logger(__name__)

try:
    result = 1 / 0
except ZeroDivisionError:
    # Logs exception with full traceback
    logger.exception("Division by zero occurred")
```

## How It Works

Under the hood, `mplog` uses Python's `QueueHandler` and `QueueListener` pattern:

1. A `multiprocessing.Manager().Queue()` is created for inter-process communication
2. All loggers use a `QueueHandler` that sends log records to this queue
3. A `QueueListener` in the main process reads from the queue and dispatches to actual handlers (file, stderr)
4. This ensures only one process writes to files/streams, avoiding conflicts

The library uses a singleton pattern to ensure the logging setup is consistent across all processes.

## Differences from Standard Logging

**Standard logging:**
```python
import logging

# Can cause issues with multiprocessing
logging.basicConfig(
    level=logging.INFO,
    filename='app.log',
    format='%(message)s'
)
```

**mplog:**
```python
from mplog import setup_logging, get_logger

# Safe for multiprocessing and asyncio
setup_logging(level='INFO', log_file='app.log')
logger = get_logger(__name__)
```

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## Thread Safety

The library is thread-safe and process-safe. You can safely:
- Log from multiple threads in the same process
- Log from multiple processes
- Log from asyncio coroutines
- Mix all of the above

## Best Practices

1. **Call `setup_logging()` once** in your main module before spawning processes
2. **Use `get_logger(__name__)`** in each module for better log organization
3. **Use appropriate log levels**: DEBUG < INFO < WARNING < ERROR < CRITICAL
4. **Enable log rotation** for long-running applications to prevent huge log files

## License

This is free and unencumbered software released into the public domain.

## See Also

Run `python mplog_examples.py` to see various usage patterns in action!
