"""
Logging utility for Wan Worker
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(log_dir="./logs", worker_id="worker"):
    """
    Setup logger with both file and console output

    Args:
        log_dir: Directory to store log files
        worker_id: Worker identification for log filename

    Returns:
        Logger instance
    """
    # Create log directory if not exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger("WanWorker")
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    logger.handlers = []

    # File handler
    log_file = log_path / f"{worker_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Formatter (no special characters, clean format)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log_task_start(logger, task_id, job_id):
    """Log task start"""
    logger.info("="*60)
    logger.info(f"TASK START - task_id: {task_id}, job_id: {job_id}")
    logger.info("="*60)


def log_task_complete(logger, task_id, status):
    """Log task completion"""
    logger.info("="*60)
    logger.info(f"TASK COMPLETE - task_id: {task_id}, status: {status}")
    logger.info("="*60)


def log_step(logger, step, message):
    """Log a step in the process"""
    logger.info(f"[STEP {step}] {message}")


def log_error(logger, error_msg, exception=None):
    """Log error with optional exception"""
    logger.error(f"ERROR: {error_msg}")
    if exception:
        logger.error(f"Exception: {str(exception)}")
