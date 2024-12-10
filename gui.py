import tkinter as tk
from tkinter import ttk, messagebox
from stress_test import start_test

def create_gui():
    # Create the main window
    root = tk.Tk()
    root.title("CPU Stress Test")

    # Instructions
    instructions = tk.Label(root, text="Instructions:\n"
                                   "1. Task Size (Recommended: 50,000–100,000): High for peak performance testing, low for quicker results.\n"
                                   "2. Duration: Long (60–120s) for detailed check, short for a quick check.\n")
    instructions.pack(pady=10)

    # Task size input
    task_size_label = tk.Label(root, text="Enter Task Size (50,000 - 100,000):")
    task_size_label.pack()
    task_size_entry = tk.Entry(root)
    task_size_entry.pack(pady=5)
    task_size_entry.insert(0, "50000")  # Default task size

    # Test duration input
    duration_label = tk.Label(root, text="Enter Test Duration (in seconds):")
    duration_label.pack()
    duration_entry = tk.Entry(root)
    duration_entry.pack(pady=5)
    duration_entry.insert(0, "120")  # Default duration

    # Progress bar
    progress_bar = ttk.Progressbar(root, length=300, mode="determinate", maximum=100)
    progress_bar.pack(pady=10)

    # Progress label
    progress_label = tk.Label(root, text="Progress: 0 tasks completed.")
    progress_label.pack(pady=10)

    # Loading label (initially hidden)
    loading_label = tk.Label(root, text="Running Benchmark", font=("Arial", 12), fg="red")
    loading_label.pack_forget()  # Hide it initially

    # Start button
    start_button = tk.Button(
        root, text="Start Test",
        command=lambda: start_test(
            int(task_size_entry.get()), int(duration_entry.get()),
            progress_bar, progress_label, start_button, loading_label,
            task_size_entry, duration_entry, root
        )
    )
    start_button.pack(pady=20)

    # Start the Tkinter event loop
    root.mainloop()