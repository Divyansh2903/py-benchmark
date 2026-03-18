import os
import platform
import subprocess
import threading
import time
import customtkinter as ctk
from stress_test import stress_test, validate_inputs

# ── Palette ─────────────────────────────────────────────────────────
BG        = "#141417"
SURFACE   = "#1C1C21"
CARD      = "#222228"
BORDER    = "#2C2C34"
BORDER_LT = "#35353F"

TEXT       = "#D4D4D8"
TEXT_DIM   = "#8E8E96"
TEXT_FAINT = "#56565E"

ACCENT       = "#7B8AEC"
ACCENT_HOVER = "#6B7AD8"
GREEN        = "#6BC77C"
RED_SOFT     = "#D4605A"
AMBER        = "#C9985A"

FONT = "Helvetica Neue"


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


def _cpu_brand() -> str:
    """
    Best-effort CPU name for display/copy.
    On macOS, platform.processor() can be a generic "arm".
    """
    if platform.system() == "Darwin":
        try:
            brand = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if brand:
                return brand
        except Exception:
            pass
    return platform.processor() or platform.machine()


def _cpu_display_name() -> str:
    cores = os.cpu_count() or 1
    brand = _cpu_brand()
    if brand.startswith("Apple "):
        brand = brand.removeprefix("Apple ").strip()
    if brand.lower() == "arm":
        brand = platform.machine()
    return f"{brand} {cores}-core"


def _device_label() -> str:
    return platform.node() or platform.system()


def _ram_gb_label() -> str:
    """
    Best-effort system RAM in whole GB for the copy row.
    Returns "?" if detection fails.
    """
    try:
        sysname = platform.system()
        if sysname == "Darwin":
            mem = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            b = int(mem)
            gb = int(round(b / (1024 ** 3)))
            return str(gb)
        if sysname == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        gb = int(round(kb / (1024 ** 2)))
                        return str(gb)
        if sysname == "Windows":
            out = subprocess.check_output(
                ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            digits = "".join(ch for ch in out if ch.isdigit())
            if digits:
                b = int(digits)
                gb = int(round(b / (1024 ** 3)))
                return str(gb)
    except Exception:
        pass
    return "?"


def _cpu_label() -> str:
    return _cpu_display_name()


def create_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("CPU Stress Tool")
    root.geometry("540x720")
    root.minsize(480, 600)
    root.configure(fg_color=BG)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    outer = ctk.CTkScrollableFrame(
        root, fg_color="transparent", corner_radius=0,
        scrollbar_button_color=BORDER, scrollbar_button_hover_color=BORDER_LT,
    )
    outer.grid(row=0, column=0, sticky="nsew", padx=32, pady=32)
    outer.columnconfigure(0, weight=1)

    # ── Benchmark state ─────────────────────────────────────────────
    cancel_event = threading.Event()
    state = {
        "running": False,
        "t0": 0.0,
        "duration": 0,
        "timer_id": None,
        "result": None,       # (metric, task_count, total_time)
    }

    # ── Header ──────────────────────────────────────────────────────
    ctk.CTkLabel(
        outer, text="CPU Stress Tool",
        font=(FONT, 22, "bold"), text_color=TEXT, anchor="w",
    ).grid(row=0, column=0, sticky="w")

    ctk.CTkLabel(
        outer,
        text="Saturate all cores with a CPU-bound workload and measure throughput.",
        font=(FONT, 12), text_color=TEXT_DIM, anchor="w",
    ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    ctk.CTkLabel(
        outer, text=_cpu_label(),
        font=(FONT, 11), text_color=TEXT_FAINT, anchor="w",
    ).grid(row=2, column=0, sticky="w", pady=(6, 0))

    # ── Settings Card ───────────────────────────────────────────────
    settings = _card(outer, row=3, pady=(20, 0))
    settings.columnconfigure(1, weight=1)
    _section_label(settings, "Configuration", row=0)

    def digits_only(v: str) -> bool:
        return v.isdigit() or v == ""
    vcmd = (root.register(digits_only), "%P")

    _field_label(settings, "Task size", row=1)
    task_size_entry = _entry(settings, row=1, vcmd=vcmd)
    task_size_entry.insert(0, "50000")

    _field_label(settings, "Duration (s)", row=2, pady=(0, 0))
    duration_entry = _entry(settings, row=2, pady=(0, 0))
    duration_entry.insert(0, "120")

    presets_frame = ctk.CTkFrame(settings, fg_color="transparent")
    presets_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 16))

    def apply_preset(ts: int, dur: int) -> None:
        task_size_entry.delete(0, "end")
        task_size_entry.insert(0, str(ts))
        duration_entry.delete(0, "end")
        duration_entry.insert(0, str(dur))

    for i, (label, ts, dur) in enumerate([
        ("Quick  30s", 50000, 30),
        ("Standard  120s", 50000, 120),
        ("Heavy  180s", 100000, 180),
    ]):
        ctk.CTkButton(
            presets_frame, text=label, width=110, height=28, corner_radius=6,
            fg_color="transparent", border_color=BORDER_LT, border_width=1,
            text_color=TEXT_DIM, hover_color=SURFACE, font=(FONT, 11),
            command=lambda t=ts, d=dur: apply_preset(t, d),
        ).grid(row=0, column=i, padx=(0, 6))

    # ── Status Card ─────────────────────────────────────────────────
    status_card = _single_col_card(outer, row=4, pady=(12, 0))
    _section_label(status_card, "Status", row=0, colspan=1)

    progress_bar = ctk.CTkProgressBar(
        status_card, height=6, corner_radius=3,
        fg_color=BORDER, progress_color=ACCENT,
    )
    progress_bar.grid(row=1, column=0, sticky="ew", padx=16)
    progress_bar.set(0)

    progress_label = ctk.CTkLabel(
        status_card, text="Idle",
        font=(FONT, 12), text_color=TEXT_DIM, anchor="w",
    )
    progress_label.grid(row=2, column=0, sticky="w", padx=16, pady=(8, 4))

    status_label = ctk.CTkLabel(
        status_card, text="",
        font=(FONT, 11), text_color=RED_SOFT, anchor="w",
    )
    status_label.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 16))

    # ── Result Card ─────────────────────────────────────────────────
    result_card = _single_col_card(outer, row=5, pady=(12, 0))
    _section_label(result_card, "Result", row=0, colspan=1)

    result_label = ctk.CTkLabel(
        result_card, text="—",
        font=(FONT, 12), text_color=TEXT_DIM, anchor="w", justify="left",
    )
    result_label.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 16))

    # ── Action Buttons ──────────────────────────────────────────────
    actions = ctk.CTkFrame(outer, fg_color="transparent")
    actions.grid(row=6, column=0, sticky="ew", pady=(18, 0))
    actions.columnconfigure(0, weight=1)

    copy_button = ctk.CTkButton(
        actions, text="Copy", width=90, height=36, corner_radius=8,
        fg_color="transparent", border_color=BORDER_LT, border_width=1,
        text_color=TEXT_FAINT, hover_color=SURFACE,
        font=(FONT, 12), state="disabled",
        command=lambda: _copy_result(),
    )
    copy_button.grid(row=0, column=0, sticky="w")

    start_button = ctk.CTkButton(
        actions, text="Run benchmark", width=140, height=36, corner_radius=8,
        fg_color=ACCENT, hover_color=ACCENT_HOVER,
        text_color="#FFFFFF", font=(FONT, 13, "bold"),
        command=lambda: _start_benchmark(),
    )
    start_button.grid(row=0, column=1, sticky="e")

    # ── Orchestration ───────────────────────────────────────────────

    def _start_benchmark():
        if state["running"]:
            return
        try:
            ts, dur = validate_inputs(task_size_entry.get(), duration_entry.get())
        except (ValueError, TypeError) as e:
            status_label.configure(text=str(e), text_color=RED_SOFT)
            return

        state.update(running=True, t0=time.time(), duration=dur, result=None)
        cancel_event.clear()

        task_size_entry.configure(state="disabled")
        duration_entry.configure(state="disabled")
        copy_button.configure(state="disabled")
        result_label.configure(text="—")
        progress_bar.set(0)
        status_label.configure(text="Running…", text_color=AMBER)

        start_button.configure(
            text="Cancel", fg_color="transparent",
            border_color=BORDER_LT, border_width=1,
            text_color=TEXT_DIM, hover_color=SURFACE,
            command=lambda: _cancel_benchmark(),
        )

        _tick()
        threading.Thread(target=_worker, args=(ts, dur), daemon=True).start()

    def _cancel_benchmark():
        if not state["running"]:
            return
        cancel_event.set()
        status_label.configure(text="Cancelling…", text_color=AMBER)

    def _tick():
        if not state["running"]:
            return
        elapsed = time.time() - state["t0"]
        dur = state["duration"]
        progress_bar.set(min(elapsed / dur, 1.0) if dur else 0)
        progress_label.configure(
            text=f"{_fmt_time(elapsed)} / {_fmt_time(dur)}"
        )
        state["timer_id"] = root.after(500, _tick)

    def _worker(task_size, duration):
        try:
            metric, count, elapsed = stress_test(
                task_size, duration, cancel_event=cancel_event,
            )
            cancelled = cancel_event.is_set()
            root.after(0, lambda: _finalize(metric, count, elapsed, cancelled))
        except Exception as exc:
            root.after(0, lambda: _on_error(str(exc)))

    def _finalize(metric, count, total_time, cancelled):
        state["running"] = False
        _stop_timer()

        if cancelled:
            progress_bar.set(0)
            progress_label.configure(text=f"Cancelled after {_fmt_time(total_time)}")
            status_label.configure(text="Cancelled", text_color=AMBER)
        else:
            progress_bar.set(1.0)
            progress_label.configure(
                text=f"Done — {count} tasks in {_fmt_time(total_time)}"
            )
            status_label.configure(text="Completed", text_color=GREEN)
            state["result"] = (metric, count, total_time)
            result_label.configure(
                text=(
                    f"Performance:  {metric:.2f} tasks/sec\n"
                    f"Total Tasks:    {count}\n"
                    f"Total Time:     {total_time:.2f}s"
                )
            )
            copy_button.configure(state="normal")

        _reset_controls()

    def _on_error(msg):
        state["running"] = False
        _stop_timer()
        progress_bar.set(0)
        status_label.configure(text=msg, text_color=RED_SOFT)
        _reset_controls()

    def _stop_timer():
        tid = state.get("timer_id")
        if tid is not None:
            root.after_cancel(tid)
            state["timer_id"] = None

    def _reset_controls():
        start_button.configure(
            text="Run benchmark", fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#FFFFFF", border_width=0,
            command=lambda: _start_benchmark(),
        )
        task_size_entry.configure(state="normal")
        duration_entry.configure(state="normal")

    def _copy_result():
        r = state["result"]
        if not r:
            return
        metric, count, _ = r
        cpu = _cpu_display_name()
        ram_gb = _ram_gb_label()
        row = f"| <device> | {cpu} | {ram_gb} | {metric:.2f} | {count} |"
        root.clipboard_clear()
        root.clipboard_append(row)
        copy_button.configure(text="Copied!")
        root.after(1500, lambda: copy_button.configure(text="Copy"))

    # ── Keyboard shortcuts ──────────────────────────────────────────
    root.bind("<Return>", lambda _: _start_benchmark() if not state["running"] else None)
    root.bind("<Escape>", lambda _: _cancel_benchmark() if state["running"] else None)

    root.mainloop()


# ── Widget helpers ──────────────────────────────────────────────────

def _card(parent, row, pady=(0, 0)):
    f = ctk.CTkFrame(
        parent, fg_color=CARD, corner_radius=10,
        border_color=BORDER, border_width=1,
    )
    f.grid(row=row, column=0, sticky="ew", pady=pady)
    f.columnconfigure(0, weight=0)
    f.columnconfigure(1, weight=1)
    return f


def _single_col_card(parent, row, pady=(0, 0)):
    f = ctk.CTkFrame(
        parent, fg_color=CARD, corner_radius=10,
        border_color=BORDER, border_width=1,
    )
    f.grid(row=row, column=0, sticky="ew", pady=pady)
    f.columnconfigure(0, weight=1)
    return f


def _section_label(parent, text, row, colspan=2):
    ctk.CTkLabel(
        parent, text=text, font=(FONT, 11), text_color=TEXT_FAINT,
    ).grid(row=row, column=0, columnspan=colspan, sticky="w", padx=16, pady=(14, 8))


def _field_label(parent, text, row, pady=(0, 8)):
    ctk.CTkLabel(
        parent, text=text, font=(FONT, 12), text_color=TEXT_DIM,
    ).grid(row=row, column=0, sticky="w", padx=(16, 10), pady=pady)


def _entry(parent, row, vcmd=None, pady=(0, 8)):
    e = ctk.CTkEntry(
        parent, height=34, corner_radius=6,
        fg_color=SURFACE, border_color=BORDER, border_width=1,
        text_color=TEXT, font=(FONT, 12),
        validate="key", validatecommand=vcmd,
    )
    e.grid(row=row, column=1, sticky="ew", padx=(0, 16), pady=pady)
    return e
