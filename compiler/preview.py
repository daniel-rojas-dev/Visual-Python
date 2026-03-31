"""
preview.py — Live preview window.
Spawns the generated app in a subprocess for testing without compilation.
"""
import os
import sys
import subprocess
import tempfile
import customtkinter as ctk
from config import ThemeManager
from utils.threading_utils import thread_pool


class PreviewWindow:
    """Manages the preview subprocess."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._temp_file: str = ""

    def start(self, code: str, on_error=None) -> None:
        """Launch preview in a subprocess."""
        self.stop()  # Kill existing preview

        # Write code to a temp file
        try:
            fd, self._temp_file = tempfile.mkstemp(suffix=".py", prefix="vp_preview_")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as e:
            if on_error:
                on_error(f"Failed to create temp file: {e}")
            return

        def launch():
            try:
                self._process = subprocess.Popen(
                    [sys.executable, self._temp_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                self._process.wait()
                # Check for errors after process ends
                if self._process.returncode != 0:
                    stderr = self._process.stderr.read().decode("utf-8", errors="replace")
                    return ("error", stderr[-500:] if stderr else "Unknown error")
                return ("success", None)
            except Exception as e:
                return ("error", str(e))

        def on_result(result):
            status, msg = result
            if status == "error" and on_error:
                on_error(msg)
            self._cleanup_temp()

        def on_exc(exc):
            if on_error:
                on_error(str(exc))
            self._cleanup_temp()

        thread_pool.run_in_thread(launch, on_result, on_exc)

    def stop(self) -> None:
        """Kill the preview subprocess."""
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
        self._process = None
        self._cleanup_temp()

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _cleanup_temp(self) -> None:
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.unlink(self._temp_file)
            except Exception:
                pass
            self._temp_file = ""


class PreviewPanel(ctk.CTkFrame):
    """UI panel with Preview and Compile buttons."""

    def __init__(self, parent, on_preview=None, on_compile=None,
                 on_export_py=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_preview = on_preview
        self._on_compile = on_compile
        self._on_export_py = on_export_py
        colors = ThemeManager.colors()
        self.configure(fg_color=colors["bg_secondary"], corner_radius=0)

        ctk.CTkLabel(self, text="🚀 Build & Run",
                     font=("Segoe UI", 13, "bold"),
                     text_color=colors["fg_accent"]).pack(padx=10, pady=(10, 6), anchor="w")

        sep = ctk.CTkFrame(self, height=1, fg_color=colors["border"])
        sep.pack(fill="x", padx=10, pady=(0, 8))

        # Preview button
        ctk.CTkButton(
            self, text="▶️  Preview",
            font=("Segoe UI", 13, "bold"),
            height=36,
            fg_color=colors["success"],
            hover_color="#27ae60",
            corner_radius=8,
            command=self._preview).pack(fill="x", padx=12, pady=4)

        # Export .py button
        ctk.CTkButton(
            self, text="📄  Export .py",
            font=("Segoe UI", 13),
            height=34,
            fg_color=colors["fg_accent"],
            hover_color=colors["fg_accent2"],
            corner_radius=8,
            command=self._export_py).pack(fill="x", padx=12, pady=4)

        # Compile .exe button
        ctk.CTkButton(
            self, text="📦  Compile .exe",
            font=("Segoe UI", 13),
            height=34,
            fg_color=colors["fg_accent2"],
            hover_color="#6c2bd9",
            corner_radius=8,
            command=self._compile).pack(fill="x", padx=12, pady=4)

        # Status label
        self.status = ctk.CTkLabel(
            self, text="",
            font=("Segoe UI", 10),
            text_color="#808080",
            wraplength=180)
        self.status.pack(padx=10, pady=(8, 4))

    def _preview(self) -> None:
        if self._on_preview:
            self._on_preview()

    def _export_py(self) -> None:
        if self._on_export_py:
            self._on_export_py()

    def _compile(self) -> None:
        if self._on_compile:
            self._on_compile()

    def set_status(self, text: str) -> None:
        self.status.configure(text=text)
