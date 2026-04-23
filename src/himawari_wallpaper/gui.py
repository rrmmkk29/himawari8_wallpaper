import argparse
import os
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .app import update_once
from .autostart import get_startup_entry_path, has_startup, install_startup, remove_startup
from .config import AppConfig, build_runtime_config, config_to_file_values, save_config_file
from .platforms import MACOS, WINDOWS, detect_platform, enable_windows_dpi_awareness
from .uninstall import CleanupResult, perform_cleanup_actions, resolve_cleanup_config_path
from .wallpaper import set_lock_screen


def main(initial_config: AppConfig | None = None) -> None:
    config = initial_config or _build_default_config()
    enable_windows_dpi_awareness()
    root = tk.Tk()
    root.title("Himawari Wallpaper Settings")
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    target_width = min(1160, max(820, screen_width - 96))
    target_height = min(700, max(560, screen_height - 96))
    root.geometry(f"{target_width}x{target_height}")
    root.minsize(min(target_width, 940), min(target_height, 620))

    _configure_styles(root)

    state = _GuiState.from_config(config)
    _build_window(root, state)
    root.mainloop()


def _build_default_config() -> AppConfig:
    config_path = _get_default_config_path()
    args = _build_args(config=str(config_path) if config_path.exists() else None)
    config = build_runtime_config(args)
    if config.config_path is None:
        config = replace(config, config_path=config_path)
    return config


def _build_args(**overrides) -> argparse.Namespace:
    defaults = {
        "run": False,
        "once": False,
        "install_startup": False,
        "remove_startup": False,
        "gui": False,
        "config": None,
        "interval": 3600,
        "zoom": 0,
        "max_zoom": 8,
        "out": None,
        "earth_height_ratio": 0.6,
        "y_offset_ratio": 0.0,
        "apply_wallpaper": True,
        "sync_lock_screen": False,
        "target_url": "https://himawari.asia/",
        "navigation_timeout_ms": 120000,
        "warmup_wait_ms": 15000,
        "probe_step_seconds": 600,
        "probe_lookback_steps": 36,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class _GuiState:
    def __init__(self, config: AppConfig) -> None:
        current_platform = detect_platform()
        self.config_path = tk.StringVar(
            value=_display_path(config.config_path or _get_default_config_path())
        )
        self.output_dir = tk.StringVar(value=_display_path(config.output_dir))
        self.interval = tk.StringVar(value=str(config.interval_sec))
        self.max_zoom = tk.StringVar(value=str(config.max_zoom))
        self.earth_height_ratio = tk.StringVar(value=str(config.earth_height_ratio))
        self.y_offset_ratio = tk.StringVar(value=str(config.y_offset_ratio))
        self.target_url = tk.StringVar(value=config.target_url)
        self.navigation_timeout_ms = tk.StringVar(value=str(config.navigation_timeout_ms))
        self.warmup_wait_ms = tk.StringVar(value=str(config.warmup_wait_ms))
        self.apply_wallpaper = tk.BooleanVar(value=config.apply_wallpaper)
        self.sync_lock_screen = tk.BooleanVar(value=config.sync_lock_screen)
        self.status_text = tk.StringVar(value="Ready.")
        self.platform_text = tk.StringVar(value=f"Platform: {_format_platform_label(current_platform)}")
        self.startup_text = tk.StringVar(value=_format_startup_status())
        self.startup_hint_text = tk.StringVar(value=_format_startup_hint())
        self.startup_enabled = tk.BooleanVar(value=has_startup())
        self.syncing_startup_toggle = False
        self.latest_wallpaper_text = tk.StringVar(value=_format_latest_wallpaper_status(config.output_dir))
        self.browser_fallback_text = tk.StringVar(value=_format_browser_fallback_details())
        self.browser_install_in_progress = False
        self.log_widget: tk.Text | None = None

    @classmethod
    def from_config(cls, config: AppConfig) -> "_GuiState":
        return cls(config)


def _build_window(root: tk.Tk, state: _GuiState) -> None:
    lock_screen_supported = _is_lock_screen_supported()

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    container = ttk.Frame(root, padding=12)
    container.grid(sticky="nsew")
    container.columnconfigure(0, weight=3)
    container.columnconfigure(1, weight=2)
    container.rowconfigure(1, weight=1)

    header = ttk.Frame(container)
    header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
    header.columnconfigure(0, weight=1)

    ttk.Label(
        header,
        text="Himawari Dynamic Wallpaper",
        style="PageTitle.TLabel",
    ).grid(row=0, column=0, sticky="w")
    ttk.Label(
        header,
        textvariable=state.platform_text,
        style="HeaderMeta.TLabel",
    ).grid(row=0, column=1, sticky="e")

    settings_frame = ttk.LabelFrame(container, text="Settings", style="Section.TLabelframe")
    settings_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
    settings_frame.columnconfigure(0, weight=1)
    settings_frame.columnconfigure(1, weight=1)

    paths_frame = ttk.Frame(settings_frame, padding=(8, 6, 8, 2))
    paths_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
    for column, weight in ((0, 0), (1, 1), (2, 0), (3, 0), (4, 1), (5, 0)):
        paths_frame.columnconfigure(column, weight=weight)
    _add_inline_path_field(paths_frame, 0, "Config", state.config_path, _pick_config_file)
    _add_inline_path_field(paths_frame, 3, "Output", state.output_dir, _pick_output_dir)

    basic_frame = ttk.LabelFrame(settings_frame, text="Refresh + image")
    basic_frame.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=(0, 6))
    basic_frame.columnconfigure(1, weight=1)
    basic_frame.columnconfigure(3, weight=1)
    row = 0
    row = _add_entry_pair_row(
        basic_frame,
        row,
        "Interval",
        state.interval,
        "Max zoom",
        state.max_zoom,
        second_values=("1", "2", "4", "8"),
    )
    row = _add_entry_pair_row(
        basic_frame,
        row,
        "Earth ratio",
        state.earth_height_ratio,
        "Y offset",
        state.y_offset_ratio,
    )

    advanced_frame = ttk.LabelFrame(settings_frame, text="Network + behavior")
    advanced_frame.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=(0, 6))
    advanced_frame.columnconfigure(1, weight=1)
    advanced_frame.columnconfigure(3, weight=1)
    row = 0
    row = _add_entry_pair_row(
        advanced_frame,
        row,
        "Nav timeout",
        state.navigation_timeout_ms,
        "Warmup wait",
        state.warmup_wait_ms,
    )
    ttk.Label(advanced_frame, text="URL").grid(
        row=row,
        column=0,
        sticky="w",
        padx=(8, 8),
        pady=4,
    )
    url_entry = ttk.Entry(advanced_frame, textvariable=state.target_url)
    url_entry.grid(
        row=row,
        column=1,
        columnspan=3,
        sticky="ew",
        padx=(0, 8),
        pady=4,
    )
    _bind_tooltip(url_entry, state.target_url)
    row += 1

    options = ttk.Frame(advanced_frame)
    options.grid(row=row, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 6))
    ttk.Checkbutton(
        options,
        text="Apply wallpaper",
        variable=state.apply_wallpaper,
    ).grid(row=0, column=0, sticky="w", padx=(0, 12))
    lock_screen_toggle = ttk.Checkbutton(
        options,
        text="Sync lock screen",
        variable=state.sync_lock_screen,
    )
    lock_screen_toggle.grid(row=0, column=1, sticky="w")
    if not lock_screen_supported:
        state.sync_lock_screen.set(False)
        lock_screen_toggle.state(["disabled"])

    sidebar = ttk.Frame(container)
    sidebar.grid(row=1, column=1, sticky="nsew")
    sidebar.columnconfigure(0, weight=1)

    status_frame = ttk.LabelFrame(sidebar, text="Current status", style="Section.TLabelframe")
    status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    status_frame.columnconfigure(0, weight=1)
    status_label = ttk.Label(
        status_frame,
        textvariable=state.status_text,
        style="StatusValue.TLabel",
        wraplength=290,
        justify="left",
    )
    status_label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 6))
    _bind_tooltip(status_label, state.status_text)
    latest_label = ttk.Label(
        status_frame,
        textvariable=state.latest_wallpaper_text,
        wraplength=290,
        justify="left",
    )
    latest_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))
    _bind_tooltip(latest_label, state.latest_wallpaper_text)
    startup_label = ttk.Label(
        status_frame,
        textvariable=state.startup_text,
        wraplength=290,
        justify="left",
    )
    startup_label.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 8))
    _bind_tooltip(startup_label, state.startup_text)

    run_frame = ttk.LabelFrame(sidebar, text="Run", style="Section.TLabelframe")
    run_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))
    run_frame.columnconfigure(0, weight=1)
    run_frame.columnconfigure(1, weight=1)
    tk.Button(
        run_frame,
        text="Run now",
        command=lambda: _run_once(root, state),
        font=("Segoe UI", 11, "bold"),
        bg="#2563eb",
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        relief="flat",
        bd=0,
        padx=16,
        pady=8,
        cursor="hand2",
    ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 6))
    ttk.Button(
        run_frame,
        text="Save config",
        command=lambda: _save_config(state),
        style="Action.TButton",
    ).grid(row=1, column=0, sticky="ew", padx=(10, 5), pady=(0, 6))
    ttk.Button(
        run_frame,
        text="Preview latest",
        command=lambda: _preview_latest_wallpaper(state),
        style="Action.TButton",
    ).grid(row=1, column=1, sticky="ew", padx=(5, 10), pady=(0, 6))
    ttk.Button(
        run_frame,
        text="Open output",
        command=lambda: _open_output_dir(state),
        style="Action.TButton",
    ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))

    system_frame = ttk.LabelFrame(sidebar, text="Environment", style="Section.TLabelframe")
    system_frame.grid(row=2, column=0, sticky="nsew")
    for column in range(2):
        system_frame.columnconfigure(column, weight=1)
    ttk.Checkbutton(
        system_frame,
        text="Enable startup at login",
        variable=state.startup_enabled,
        command=lambda: _toggle_startup(state),
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 3))
    system_details_label = ttk.Label(
        system_frame,
        text=_format_startup_toggle_details(),
        style="Subtle.TLabel",
        wraplength=290,
        justify="left",
    )
    system_details_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
    _bind_static_tooltip(system_details_label, _format_startup_toggle_details())
    ttk.Button(
        system_frame,
        text="Install browser fallback",
        command=lambda: _install_browser_fallback(root, state),
        style="Action.TButton",
    ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 3))
    browser_label = ttk.Label(
        system_frame,
        textvariable=state.browser_fallback_text,
        style="Subtle.TLabel",
        wraplength=290,
        justify="left",
    )
    browser_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
    _bind_tooltip(browser_label, state.browser_fallback_text)
    lock_screen_button = ttk.Button(
        system_frame,
        text="Test lock",
        command=lambda: _test_lock_screen(state),
        style="Action.TButton",
    )
    lock_screen_button.grid(row=4, column=0, sticky="ew", padx=(10, 5), pady=(0, 8))
    if not lock_screen_supported:
        lock_screen_button.state(["disabled"])
    ttk.Button(
        system_frame,
        text="Cleanup",
        command=lambda: _cleanup_uninstall(root, state),
        style="Action.TButton",
    ).grid(row=4, column=1, sticky="ew", padx=(5, 10), pady=(0, 8))

    log_frame = ttk.LabelFrame(container, text="Activity log", style="Section.TLabelframe")
    log_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
    log_frame.columnconfigure(0, weight=1)
    log_widget = tk.Text(log_frame, height=3, wrap="word", relief="flat", borderwidth=0)
    log_widget.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
    log_widget.insert("end", "GUI ready.\n")
    log_widget.configure(state="disabled")
    state.log_widget = log_widget


def _configure_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.configure("PageTitle.TLabel", font=("Segoe UI", 17, "bold"))
    style.configure("HeaderMeta.TLabel", font=("Segoe UI", 10, "bold"))
    style.configure("Subtle.TLabel", font=("Segoe UI", 8))
    style.configure("StatusValue.TLabel", font=("Segoe UI", 9, "bold"))
    style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
    style.configure("Action.TButton", padding=(8, 5))
    style.configure("PathValue.TLabel", padding=(8, 5), relief="solid", borderwidth=1)
    style.configure("Tooltip.TLabel", background="#fffbe6", relief="solid", borderwidth=1, padding=6)


def _get_default_config_path() -> Path:
    candidates = _get_default_config_candidates()
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def _get_default_config_candidates() -> tuple[Path, ...]:
    candidates: list[Path] = []

    bundle_root = _get_bundle_root()
    if bundle_root is not None:
        candidates.append(bundle_root / "config.json")

    cwd_config = Path.cwd() / "config.json"
    candidates.append(cwd_config)

    project_root = _find_project_root()
    if project_root is not None:
        project_config = project_root / "config.json"
        if project_config not in candidates:
            candidates.append(project_config)

    return tuple(candidates)


def _get_bundle_root() -> Path | None:
    from .autostart import BUNDLE_MARKERS

    executable = Path(sys.executable).resolve()
    candidates = (executable.parent, executable.parent.parent)

    for candidate in candidates:
        if any((candidate / marker).exists() for marker in BUNDLE_MARKERS):
            return candidate

    return None


def _get_preferred_python_executable() -> str:
    from .autostart import _resolve_python_executable

    return _resolve_python_executable(background=False)


def _add_entry_pair_row(
    parent: ttk.Frame,
    row: int,
    first_label: str,
    first_variable: tk.StringVar,
    second_label: str,
    second_variable: tk.StringVar,
    second_values: tuple[str, ...] | None = None,
) -> int:
    ttk.Label(parent, text=first_label).grid(
        row=row,
        column=0,
        sticky="w",
        padx=(10, 8),
        pady=4,
    )
    ttk.Entry(parent, textvariable=first_variable).grid(
        row=row,
        column=1,
        sticky="ew",
        padx=(0, 12),
        pady=4,
    )
    ttk.Label(parent, text=second_label).grid(
        row=row,
        column=2,
        sticky="w",
        padx=(0, 8),
        pady=4,
    )
    if second_values is None:
        field = ttk.Entry(parent, textvariable=second_variable)
    else:
        field = ttk.Combobox(
            parent,
            textvariable=second_variable,
            values=second_values,
            state="readonly",
        )
    field.grid(
        row=row,
        column=3,
        sticky="ew",
        padx=(0, 10),
        pady=4,
    )
    return row + 1


def _add_path_row(
    parent: ttk.Frame,
    row: int,
    label: str,
    variable: tk.StringVar,
    picker,
) -> int:
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
    preview_text = tk.StringVar()
    _bind_truncated_text(variable, preview_text, max_length=54)
    value_label = ttk.Label(parent, textvariable=preview_text, style="PathValue.TLabel", anchor="w")
    value_label.grid(row=row, column=1, sticky="ew", pady=4)
    _bind_tooltip(value_label, variable)
    ttk.Button(parent, text="Browse", command=lambda: picker(variable)).grid(
        row=row,
        column=2,
        sticky="e",
        pady=4,
        padx=(10, 0),
    )
    return row + 1


def _add_inline_path_field(
    parent: ttk.Frame,
    column_offset: int,
    label: str,
    variable: tk.StringVar,
    picker,
) -> None:
    ttk.Label(parent, text=label).grid(
        row=0,
        column=column_offset,
        sticky="w",
        pady=4,
        padx=(0, 8),
    )
    preview_text = tk.StringVar()
    _bind_truncated_text(variable, preview_text, max_length=28)
    value_label = ttk.Label(parent, textvariable=preview_text, style="PathValue.TLabel", anchor="w")
    value_label.grid(row=0, column=column_offset + 1, sticky="ew", pady=4)
    _bind_tooltip(value_label, variable)
    ttk.Button(parent, text="...", width=3, command=lambda: picker(variable)).grid(
        row=0,
        column=column_offset + 2,
        sticky="e",
        pady=4,
        padx=(8, 0),
    )


def _add_entry_row(parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> int:
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
    ttk.Entry(parent, textvariable=variable).grid(
        row=row,
        column=1,
        columnspan=2,
        sticky="ew",
        pady=4,
    )
    return row + 1


def _add_combo_row(
    parent: ttk.Frame,
    row: int,
    label: str,
    variable: tk.StringVar,
    values: tuple[str, ...],
) -> int:
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
    ttk.Combobox(parent, textvariable=variable, values=values, state="readonly").grid(
        row=row,
        column=1,
        columnspan=2,
        sticky="ew",
        pady=4,
    )
    return row + 1


def _build_info_card(
    parent: ttk.Frame,
    column: int,
    title: str,
    primary: tk.StringVar,
    secondary: tk.StringVar | None = None,
) -> None:
    card = ttk.LabelFrame(parent, text=title)
    card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
    card.columnconfigure(0, weight=1)

    ttk.Label(
        card,
        textvariable=primary,
        wraplength=250,
        justify="left",
    ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 6))

    if secondary is not None:
        ttk.Label(
            card,
            textvariable=secondary,
            wraplength=250,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
    else:
        ttk.Label(card, text="").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))


def _pick_output_dir(variable: tk.StringVar) -> None:
    selected = filedialog.askdirectory(initialdir=variable.get() or str(Path.cwd()))
    if selected:
        variable.set(_display_path(selected))


def _pick_config_file(variable: tk.StringVar) -> None:
    selected = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        initialfile=Path(variable.get() or "config.json").name,
        initialdir=str(Path(variable.get()).parent if variable.get() else Path.cwd()),
    )
    if selected:
        variable.set(_display_path(selected))


def _display_path(value: str | Path | None) -> str:
    if value is None:
        return ""
    return os.path.normpath(str(value))


def _truncate_middle(value: str, max_length: int = 54) -> str:
    if len(value) <= max_length:
        return value
    if max_length <= 3:
        return value[:max_length]
    head = (max_length - 3) // 2
    tail = max_length - 3 - head
    return f"{value[:head]}...{value[-tail:]}"


def _bind_truncated_text(source_var: tk.StringVar, target_var: tk.StringVar, max_length: int) -> None:
    def refresh(*_args) -> None:
        target_var.set(_truncate_middle(source_var.get(), max_length=max_length))

    source_var.trace_add("write", refresh)
    refresh()


class _Tooltip:
    def __init__(self, widget: tk.Widget, text_getter) -> None:
        self.widget = widget
        self.text_getter = text_getter
        self.window: tk.Toplevel | None = None
        self.label: ttk.Label | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        text = self.text_getter()
        if not text:
            return
        if self.window is not None:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.attributes("-topmost", True)
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.window.wm_geometry(f"+{x}+{y}")
        self.label = ttk.Label(
            self.window,
            text=text,
            style="Tooltip.TLabel",
            justify="left",
            wraplength=640,
        )
        self.label.pack()

    def _hide(self, _event=None) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None
            self.label = None


def _bind_tooltip(widget: tk.Widget, variable: tk.StringVar) -> None:
    _Tooltip(widget, variable.get)


def _bind_static_tooltip(widget: tk.Widget, text: str) -> None:
    _Tooltip(widget, lambda: text)


def _config_from_state(state: _GuiState) -> tuple[AppConfig, Path]:
    config_path = Path(state.config_path.get()).expanduser()
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()
    else:
        config_path = config_path.resolve()

    args = _build_args(
        config=None,
        interval=int(state.interval.get()),
        max_zoom=int(state.max_zoom.get()),
        out=state.output_dir.get() or None,
        earth_height_ratio=float(state.earth_height_ratio.get()),
        y_offset_ratio=float(state.y_offset_ratio.get()),
        apply_wallpaper=state.apply_wallpaper.get(),
        sync_lock_screen=state.sync_lock_screen.get(),
        target_url=state.target_url.get(),
        navigation_timeout_ms=int(state.navigation_timeout_ms.get()),
        warmup_wait_ms=int(state.warmup_wait_ms.get()),
    )
    config = replace(build_runtime_config(args), config_path=config_path)
    return config, config_path


def _save_config(state: _GuiState) -> AppConfig:
    config, config_path = _config_from_state(state)
    save_config_file(config_path, config_to_file_values(config))
    _append_log(state, f"Saved config: {config_path}")
    state.status_text.set("Config saved.")
    _refresh_generated_status(state)
    return config


def _run_once(root: tk.Tk, state: _GuiState) -> None:
    def task() -> None:
        try:
            config = _save_config(state)
            update_once(config=config)
            root.after(
                0,
                lambda: _handle_run_completed(state, config.output_dir),
            )
        except Exception as exc:
            root.after(
                0,
                lambda error_message=str(exc): _show_error(state, "Run failed", error_message),
            )

    threading.Thread(target=task, daemon=True).start()
    state.status_text.set("Running update...")
    _append_log(state, "Running one update...")


def _install_startup(state: _GuiState) -> bool:
    try:
        config = _save_config(state)
        startup_path = install_startup(
            interval_sec=config.interval_sec,
            out_dir=config.output_dir,
            earth_height_ratio=config.earth_height_ratio,
            y_offset_ratio=config.y_offset_ratio,
            max_zoom=config.max_zoom,
            apply_wallpaper=config.apply_wallpaper,
            sync_lock_screen=config.sync_lock_screen,
            config_path=config.config_path,
        )
    except Exception as exc:
        _show_error(state, "Startup install failed", str(exc))
        return False

    _set_status_and_log(state, "Startup enabled.", f"Startup installed: {startup_path}")
    _refresh_startup_status(state)
    return True


def _remove_startup(state: _GuiState) -> bool:
    try:
        removed = remove_startup()
    except Exception as exc:
        _show_error(state, "Startup removal failed", str(exc))
        return False

    if removed:
        _set_status_and_log(state, "Startup disabled.", "Startup removed.")
        _refresh_startup_status(state)
        return True

    _set_status_and_log(state, "No startup entry found.", "No startup entry found.")
    _refresh_startup_status(state)
    return True


def _toggle_startup(state: _GuiState) -> None:
    if state.syncing_startup_toggle:
        return

    if state.startup_enabled.get():
        ok = _install_startup(state)
    else:
        ok = _remove_startup(state)

    if not ok:
        _refresh_startup_status(state)


def _open_output_dir(state: _GuiState) -> None:
    try:
        output_dir = _resolve_output_dir_from_state(state)
        output_dir.mkdir(parents=True, exist_ok=True)
        _open_path(output_dir)
    except Exception as exc:
        _show_error(state, "Open output folder failed", str(exc))
        return

    _set_status_and_log(state, "Output opened.", f"Opened output folder: {output_dir}")


def _install_browser_fallback(root: tk.Tk, state: _GuiState) -> None:
    if state.browser_install_in_progress:
        _set_status_and_log(
            state,
            "Browser fallback already running.",
            "Optional browser fallback install is already running.",
        )
        return

    try:
        python_executable = _get_preferred_python_executable()
    except Exception as exc:
        _show_error(state, "Browser fallback install failed", str(exc))
        return

    project_root = _find_project_root()
    steps = _build_browser_fallback_install_steps(python_executable, project_root)

    def task() -> None:
        try:
            for command, cwd in steps:
                command_text = _format_command_for_log(command, cwd)
                root.after(
                    0,
                    lambda text=command_text: _append_log(state, f"Running: {text}"),
                )
                subprocess.run(
                    command,
                    cwd=str(cwd) if cwd is not None else None,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                root.after(
                    0,
                    lambda text=command_text: _append_log(state, f"Completed: {text}"),
                )

            root.after(
                0,
                lambda: _finish_browser_fallback_install(state, project_root),
            )
        except subprocess.CalledProcessError as exc:
            root.after(
                0,
                lambda message=_format_subprocess_error(exc): _fail_browser_fallback_install(
                    state,
                    message,
                ),
            )
        except Exception as exc:
            root.after(
                0,
                lambda message=str(exc): _fail_browser_fallback_install(state, message),
            )

    state.browser_install_in_progress = True
    state.status_text.set("Installing browser fallback...")
    _append_log(state, f"Installing optional browser fallback with {python_executable}")
    threading.Thread(target=task, daemon=True).start()


def _finish_browser_fallback_install(state: _GuiState, project_root: Path | None) -> None:
    state.browser_install_in_progress = False
    source_hint = (
        f"using .[browser] from {project_root}"
        if project_root is not None
        else "using direct Playwright package install"
    )
    _set_status_and_log(
        state,
        "Browser fallback installed.",
        f"Optional browser fallback installed successfully, {source_hint}.",
    )


def _fail_browser_fallback_install(state: _GuiState, message: str) -> None:
    state.browser_install_in_progress = False
    _show_error(state, "Browser fallback install failed", message)


def _test_lock_screen(state: _GuiState) -> None:
    current_platform = detect_platform()
    if current_platform != WINDOWS:
        _show_error(
            state,
            "Lock screen test unavailable",
            "Lock screen sync is currently supported on Windows only.",
        )
        return

    try:
        output_dir = _resolve_output_dir_from_state(state)
        image_path = find_latest_generated_wallpaper(output_dir)
        if image_path is None:
            raise RuntimeError(
                "No generated wallpaper PNG was found. Run one update first, then test lock screen sync."
            )
        set_lock_screen(image_path)
    except Exception as exc:
        _show_error(state, "Lock screen test failed", str(exc))
        return

    _set_status_and_log(state, "Lock screen updated.", f"Lock screen updated from: {image_path}")


def _preview_latest_wallpaper(state: _GuiState) -> None:
    try:
        output_dir = _resolve_output_dir_from_state(state)
        image_path = find_latest_generated_wallpaper(output_dir)
        if image_path is None:
            raise RuntimeError("No generated wallpaper PNG was found. Run one update first.")
        _open_path(image_path)
    except Exception as exc:
        _show_error(state, "Preview failed", str(exc))
        return

    _set_status_and_log(state, "Preview opened.", f"Opened latest wallpaper preview: {image_path}")
    _refresh_generated_status(state)


def _cleanup_uninstall(root: tk.Tk, state: _GuiState) -> None:
    config_path = resolve_cleanup_config_path(state.config_path.get().strip() or None)
    output_dir = _resolve_output_dir_from_state(state)

    selected_actions = _show_cleanup_dialog(root, config_path=config_path, output_dir=output_dir)
    if selected_actions is None:
        _set_status_and_log(state, "Cleanup cancelled.", "Cleanup / uninstall was cancelled.")
        return

    remove_startup_flag, remove_output_flag, remove_config_flag = selected_actions
    if not any(selected_actions):
        _show_error(
            state,
            "Cleanup not selected",
            "Select at least one cleanup action before continuing.",
        )
        return

    try:
        result = perform_cleanup_actions(
            remove_startup_flag=remove_startup_flag,
            remove_output_flag=remove_output_flag,
            remove_config_flag=remove_config_flag,
            config_path=config_path,
            output_dir=output_dir,
        )
    except Exception as exc:
        _show_error(state, "Cleanup failed", str(exc))
        return

    _refresh_startup_status(state)
    _refresh_generated_status(state)
    _set_status_and_log(
        state,
        "Cleanup done.",
        _format_cleanup_result(
            result=result,
            output_dir=output_dir,
            config_path=config_path,
            requested_actions=selected_actions,
        ),
    )


def _handle_run_completed(state: _GuiState, output_dir: Path) -> None:
    state.latest_wallpaper_text.set(_format_latest_wallpaper_status(output_dir))
    _set_status_and_log(state, "Run completed.", f"Run completed. Output: {output_dir}")


def _show_error(state: _GuiState, title: str, message: str) -> None:
    state.status_text.set(message)
    _append_log(state, f"{title}: {message}")
    messagebox.showerror(title, message)


def _set_status_and_log(state: _GuiState, status: str, log_message: str) -> None:
    state.status_text.set(status)
    _append_log(state, log_message)


def _append_log(state: _GuiState, message: str) -> None:
    if state.log_widget is None:
        return

    state.log_widget.configure(state="normal")
    state.log_widget.insert("end", message + "\n")
    state.log_widget.see("end")
    state.log_widget.configure(state="disabled")


def _bind_mousewheel(root: tk.Tk, canvas: tk.Canvas) -> None:
    def on_mousewheel(event) -> None:
        if getattr(event, "delta", 0):
            canvas.yview_scroll(int(-event.delta / 120), "units")
            return
        if getattr(event, "num", None) == 4:
            canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            canvas.yview_scroll(1, "units")

    root.bind_all("<MouseWheel>", on_mousewheel)
    root.bind_all("<Button-4>", on_mousewheel)
    root.bind_all("<Button-5>", on_mousewheel)


def _resolve_output_dir_from_state(state: _GuiState) -> Path:
    raw = state.output_dir.get().strip()
    if not raw:
        raise RuntimeError("Output folder is empty.")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _refresh_startup_status(state: _GuiState) -> None:
    state.syncing_startup_toggle = True
    state.startup_text.set(_format_startup_status())
    state.startup_hint_text.set(_format_startup_hint())
    state.startup_enabled.set(has_startup())
    state.syncing_startup_toggle = False


def _refresh_generated_status(state: _GuiState) -> None:
    raw = state.output_dir.get().strip()
    if not raw:
        state.latest_wallpaper_text.set("Latest wallpaper: output folder not set")
        return
    output_dir = _resolve_output_dir_from_state(state)
    state.latest_wallpaper_text.set(_format_latest_wallpaper_status(output_dir))


def _format_startup_status() -> str:
    status = "Installed" if has_startup() else "Not installed"
    return f"Startup: {status}"


def _format_startup_hint() -> str:
    current_platform = detect_platform()
    if current_platform == WINDOWS:
        return "Uses a Startup shortcut to pythonw.exe or the bundled background runner to avoid a console window when possible."
    if current_platform == MACOS:
        return "Uses a LaunchAgent in your user Library."
    return "Uses a per-user autostart desktop entry."


def _is_lock_screen_supported() -> bool:
    return detect_platform() == WINDOWS


def _format_platform_label(platform_name: str) -> str:
    if platform_name == WINDOWS:
        return "Windows"
    if platform_name == MACOS:
        return "macOS"
    return "Linux"


def _format_startup_toggle_details() -> str:
    target = get_startup_entry_path()
    current_platform = detect_platform()
    if current_platform == WINDOWS:
        return (
            f"Entry: {_truncate_middle(str(target), 48)}\n"
            "Uses a Startup shortcut to pythonw.exe or the bundled background runner to avoid a console window when possible."
        )
    if current_platform == MACOS:
        return (
            f"Entry: {_truncate_middle(str(target), 48)}\n"
            "Creates a LaunchAgent in your user Library."
        )
    return (
        f"Entry: {_truncate_middle(str(target), 48)}\n"
        "Creates a per-user autostart desktop entry."
    )


def _format_browser_fallback_details() -> str:
    return (
        "Installs Playwright + Chromium. Prefers `.[browser]`, otherwise installs Playwright directly."
    )


def _build_cleanup_confirmation_message(config_path: Path | None, output_dir: Path) -> str:
    config_display = str(config_path) if config_path is not None else "(no config file found)"
    return (
        "This will remove the local startup entry, generated wallpaper files, and the config file.\n\n"
        f"Output folder:\n{output_dir}\n\n"
        f"Config file:\n{config_display}\n\n"
        "The currently running conda environment is not removed from the GUI.\n"
        "Continue?"
    )


def _format_cleanup_result(
    result: CleanupResult,
    output_dir: Path,
    config_path: Path | None,
    requested_actions: tuple[bool, bool, bool],
) -> str:
    requested_startup, requested_output, requested_config = requested_actions
    startup_text = "removed" if result.removed_startup else "not found"
    config_text = str(config_path) if config_path is not None else "(no config file found)"
    startup_summary = (
        f"Startup: {startup_text}"
        if requested_startup
        else "Startup: skipped"
    )
    output_summary = (
        f"output paths removed: {len(result.removed_output_paths)} from {output_dir}"
        if requested_output
        else "output cleanup: skipped"
    )
    config_summary = (
        f"config removed: {'yes' if result.removed_config else 'no'} ({config_text})"
        if requested_config
        else "config cleanup: skipped"
    )
    return (
        f"Cleanup finished. {startup_summary}; {output_summary}; {config_summary}."
    )


def _show_cleanup_dialog(
    root: tk.Tk,
    config_path: Path | None,
    output_dir: Path,
) -> tuple[bool, bool, bool] | None:
    dialog = tk.Toplevel(root)
    dialog.title("Cleanup / Uninstall")
    dialog.transient(root)
    dialog.grab_set()
    dialog.resizable(False, False)

    container = ttk.Frame(dialog, padding=16)
    container.grid(sticky="nsew")

    ttk.Label(
        container,
        text="Select the local cleanup actions to run.",
        font=("Segoe UI", 11, "bold"),
    ).grid(row=0, column=0, sticky="w", pady=(0, 10))

    ttk.Label(
        container,
        text=f"Output folder: {output_dir}",
        wraplength=560,
    ).grid(row=1, column=0, sticky="w", pady=(0, 4))
    ttk.Label(
        container,
        text=f"Config file: {config_path if config_path is not None else '(no config file found)'}",
        wraplength=560,
    ).grid(row=2, column=0, sticky="w", pady=(0, 10))

    remove_startup_var = tk.BooleanVar(value=True)
    remove_output_var = tk.BooleanVar(value=True)
    remove_config_var = tk.BooleanVar(value=True)

    ttk.Checkbutton(
        container,
        text="Remove startup entry",
        variable=remove_startup_var,
    ).grid(row=3, column=0, sticky="w", pady=2)
    ttk.Checkbutton(
        container,
        text="Remove generated wallpaper/output files",
        variable=remove_output_var,
    ).grid(row=4, column=0, sticky="w", pady=2)
    ttk.Checkbutton(
        container,
        text="Remove config.json",
        variable=remove_config_var,
    ).grid(row=5, column=0, sticky="w", pady=2)

    ttk.Label(
        container,
        text=(
            "Note: the GUI only removes local app data. "
            "The active conda environment is not removed here."
        ),
        wraplength=560,
    ).grid(row=6, column=0, sticky="w", pady=(10, 10))

    selection: dict[str, tuple[bool, bool, bool] | None] = {"value": None}

    def confirm() -> None:
        selection["value"] = (
            remove_startup_var.get(),
            remove_output_var.get(),
            remove_config_var.get(),
        )
        dialog.destroy()

    def cancel() -> None:
        selection["value"] = None
        dialog.destroy()

    buttons = ttk.Frame(container)
    buttons.grid(row=7, column=0, sticky="e")
    ttk.Button(buttons, text="Cancel", command=cancel).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(buttons, text="Run cleanup", command=confirm).grid(row=0, column=1)

    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.wait_window()
    return selection["value"]


def _find_project_root(start_paths: tuple[Path, ...] | None = None) -> Path | None:
    candidates = start_paths or (Path.cwd(), Path(__file__).resolve().parent)
    visited: set[Path] = set()

    for start in candidates:
        current = start if start.is_dir() else start.parent
        for candidate in (current, *current.parents):
            candidate = candidate.resolve()
            if candidate in visited:
                continue
            visited.add(candidate)
            if (candidate / "pyproject.toml").exists():
                return candidate

    return None


def _build_browser_fallback_install_steps(
    python_executable: str,
    project_root: Path | None,
) -> list[tuple[list[str], Path | None]]:
    steps: list[tuple[list[str], Path | None]] = []
    if project_root is not None:
        steps.append(([python_executable, "-m", "pip", "install", "-e", ".[browser]"], project_root))
    else:
        steps.append(([python_executable, "-m", "pip", "install", "playwright>=1.45.0"], None))
    steps.append(([python_executable, "-m", "playwright", "install", "chromium"], None))
    return steps


def _format_command_for_log(command: list[str], cwd: Path | None) -> str:
    command_text = " ".join(command)
    if cwd is None:
        return command_text
    return f"{command_text} (cwd: {cwd})"


def _format_subprocess_error(exc: subprocess.CalledProcessError) -> str:
    output = (exc.stderr or exc.stdout or "").strip()
    if output:
        last_line = output.splitlines()[-1]
        return f"Command failed: {' '.join(exc.cmd)}. {last_line}"
    return f"Command failed: {' '.join(exc.cmd)}."


def find_latest_generated_wallpaper(output_dir: Path) -> Path | None:
    matches = sorted(output_dir.glob("wallpaper_*.png"), key=lambda path: path.stat().st_mtime)
    if not matches:
        return None
    return matches[-1]


def _format_latest_wallpaper_status(output_dir: Path) -> str:
    latest = find_latest_generated_wallpaper(output_dir)
    if latest is None:
        return f"Latest wallpaper: none in {_truncate_middle(str(output_dir), 42)}"

    modified_at = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"Latest wallpaper: {latest.name} (updated {modified_at})"


def _open_path(path: Path) -> None:
    current_platform = detect_platform()
    if current_platform == WINDOWS:
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if current_platform == MACOS:
        subprocess.run(["open", str(path)], check=True)
        return
    subprocess.run(["xdg-open", str(path)], check=True)
