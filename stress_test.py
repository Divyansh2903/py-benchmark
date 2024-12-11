from config import log
import os
import concurrent.futures
import time
import threading
import tkinter as tk
from tkinter import messagebox
from utils import intensive_task

def stress_test(task_size, duration, report_interval=10, progress_callback=None):
    num_workers = os.cpu_count()
    log(f"Starting stress test with {num_workers} cores for {duration} seconds...")


    end_time = time.time() + duration
    task_count = 0
    start_time = time.perf_counter()

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        while time.time() < end_time:
            tasks = [task_size] * num_workers
            try:
                results = list(executor.map(intensive_task, tasks))
                task_count += len(results)
            except Exception as e:
                log(f"Error encountered during task execution: {e}")
                continue
            

            if time.time() % report_interval < 1 and progress_callback:
                elapsed_time = time.perf_counter() - start_time
                progress_callback(task_count, elapsed_time)

    total_time = time.perf_counter() - start_time
    tasks_per_second = task_count / total_time
    log(f"\nCompleted {task_count} tasks in {total_time:.2f} seconds.")
    log(f"Performance Metric: {tasks_per_second:.2f} tasks/second")
    return tasks_per_second, task_count, total_time

def start_test(task_size, test_duration, progress_bar, progress_label, start_button, loading_label, task_size_entry, duration_entry, root):
    task_size, test_duration = validate_inputs(task_size, test_duration)
    if task_size is None or test_duration is None:
        return 
    try:
        start_button.config(state="disabled")
        loading_label.config(text="Running Benchmark", fg="red")
        task_size_entry.config(state="disabled")
        duration_entry.config(state="disabled")
        progress_bar.pack(pady=10)
        loading_label.pack()

        report_interval = max(test_duration // 6, 5)

        threading.Thread(
            target=lambda: update_progress_and_metric(
                task_size, test_duration, report_interval, progress_bar,
                progress_label, start_button, loading_label, task_size_entry,
                duration_entry, root
            ), daemon=True
        ).start()

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def update_progress_and_metric(task_size, test_duration, report_interval, progress_bar, progress_label, start_button, loading_label, task_size_entry, duration_entry, root):
    try:
        for widget in root.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("text").startswith("Performance Metric"):
                widget.destroy()

        metric, task_count, total_time = stress_test(
            task_size, test_duration, report_interval,
            progress_callback=lambda count, time: update_progress(count, time, test_duration, progress_bar, progress_label)
        )

        progress_label.config(text="")
        progress_bar.pack_forget()
        loading_label.config(text="")
        
        result_label = tk.Label(progress_label.master, text=f"Performance Metric: {metric:.2f} tasks/second\nTotal Tasks: {task_count} in {total_time:.2f} seconds.", font=("Arial", 14))
        result_label.pack(pady=10)

        start_button.config(state="normal")
        task_size_entry.config(state="normal")
        duration_entry.config(state="normal")
        
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def update_progress(task_count, elapsed_time, total_duration, progress_bar, progress_label):
    progress_percentage = (elapsed_time / total_duration) * 100
    progress_bar['value'] = progress_percentage
    progress_label.config(text=f"Progress: {task_count} tasks completed.")

def validate_inputs(task_size, duration):
    try:
        task_size = int(task_size)
        duration = int(duration)
        if not (50000 <= task_size <= 100000):
            raise ValueError("Task size must be between 50,000 and 100,000.")
        if not (10 <= duration <= 3600):
            raise ValueError("Duration must be between 10 and 3600 seconds.")
        return task_size, duration
    except ValueError as ve:
        messagebox.showerror("Invalid Input", f"Error: {ve}")
        return None, None