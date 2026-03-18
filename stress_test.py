from config import log
import os
import concurrent.futures
import time
from utils import intensive_task


def stress_test(task_size, duration, cancel_event=None):
    """
    Pure CPU benchmark.  Returns (tasks_per_sec, task_count, total_time).
    If *cancel_event* is set, the loop exits early and partial results are returned.
    """
    num_workers = os.cpu_count()
    log(f"Starting stress test with {num_workers} cores for {duration} seconds...")

    start_time = time.perf_counter()
    end_time = start_time + duration
    task_count = 0

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        while time.perf_counter() < end_time:
            if cancel_event and cancel_event.is_set():
                break
            try:
                results = list(executor.map(intensive_task, [task_size] * num_workers))
                task_count += len(results)
            except Exception as e:
                log(f"Error encountered during task execution: {e}")
                continue

    total_time = time.perf_counter() - start_time
    tasks_per_second = task_count / total_time if total_time > 0 else 0
    log(f"\nCompleted {task_count} tasks in {total_time:.2f} seconds.")
    log(f"Performance Metric: {tasks_per_second:.2f} tasks/second")
    return tasks_per_second, task_count, total_time


def validate_inputs(task_size_str, duration_str):
    """Parse and validate. Returns (task_size, duration) or raises ValueError."""
    task_size = int(task_size_str)
    duration = int(duration_str)
    if not (50000 <= task_size <= 100000):
        raise ValueError("Task size must be between 50,000 and 100,000.")
    if not (10 <= duration <= 3600):
        raise ValueError("Duration must be between 10 and 3,600 seconds.")
    return task_size, duration
