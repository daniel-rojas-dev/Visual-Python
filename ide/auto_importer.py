"""
auto_importer.py — Detects missing Python packages and offers install.
Runs pip install in a background thread with progress indicator.
"""
import importlib.util
import re
import subprocess
import sys
import customtkinter as ctk
from config import ThemeManager
from utils.threading_utils import thread_pool


class AutoImporter(ctk.CTkFrame):
    """
    Scans code for import statements, detects missing packages,
    and offers one-click install via pip.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        colors = ThemeManager.colors()
        self.configure(fg_color=colors["bg_secondary"], corner_radius=8)

        self._header = ctk.CTkLabel(
            self, text="📦 Auto-Importer",
            font=("Segoe UI", 13, "bold"),
            text_color=colors["fg_accent"])
        self._header.pack(padx=10, pady=(8, 4), anchor="w")

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._status_label = ctk.CTkLabel(
            self._content, text="No missing packages",
            font=("Segoe UI", 11),
            text_color="#808080")
        self._status_label.pack(pady=8)

        self._missing: list[str] = []

    def scan_code(self, code: str) -> list[str]:
        """
        Scan code for import statements, return list of missing packages.
        """
        # Find all imports
        imports = set()
        for match in re.finditer(r'^\s*import\s+([\w.]+)', code, re.MULTILINE):
            imports.add(match.group(1).split(".")[0])
        for match in re.finditer(r'^\s*from\s+([\w.]+)\s+import', code, re.MULTILINE):
            imports.add(match.group(1).split(".")[0])

        # Check which are missing
        missing = []
        # Standard library modules to skip
        stdlib = {
            "os", "sys", "re", "json", "math", "time", "datetime",
            "threading", "subprocess", "pathlib", "functools", "copy",
            "collections", "itertools", "typing", "abc", "io",
            "uuid", "hashlib", "base64", "urllib", "http",
            "tkinter", "ctypes", "ast", "importlib", "keyword",
            "queue", "logging", "traceback", "shutil", "tempfile",
            "glob", "socket", "struct", "csv", "xml", "html",
            "email", "sqlite3", "unittest", "argparse", "textwrap",
            "configparser", "contextlib", "dataclasses", "enum",
            "inspect", "operator", "pprint", "string", "warnings",
        }

        for pkg in imports:
            if pkg in stdlib:
                continue
            if importlib.util.find_spec(pkg) is None:
                missing.append(pkg)

        self._missing = missing
        self._update_ui()
        return missing

    def _update_ui(self) -> None:
        """Update the UI with missing packages."""
        for child in self._content.winfo_children():
            child.destroy()

        colors = ThemeManager.colors()

        if not self._missing:
            ctk.CTkLabel(
                self._content, text="✅ All packages installed",
                font=("Segoe UI", 11),
                text_color=colors["success"]).pack(pady=8)
            return

        ctk.CTkLabel(
            self._content,
            text=f"⚠️ {len(self._missing)} missing package(s):",
            font=("Segoe UI", 11, "bold"),
            text_color=colors["error"]).pack(anchor="w", pady=(4, 2))

        for pkg in self._missing:
            row = ctk.CTkFrame(self._content, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=f"  📦 {pkg}",
                         font=("Consolas", 11),
                         text_color=colors["fg_text"]).pack(side="left")

            btn = ctk.CTkButton(
                row, text="Install", width=70, height=24,
                font=("Segoe UI", 10, "bold"),
                fg_color=colors["fg_accent"],
                corner_radius=4,
                command=lambda p=pkg: self._install_package(p))
            btn.pack(side="right", padx=4)

    def _install_package(self, package: str) -> None:
        """Install a package in a background thread."""
        colors = ThemeManager.colors()

        # Show progress
        for child in self._content.winfo_children():
            child.destroy()

        progress_label = ctk.CTkLabel(
            self._content,
            text=f"⏳ Installing {package}...",
            font=("Segoe UI", 11),
            text_color=colors["fg_accent"])
        progress_label.pack(pady=8)

        progress_bar = ctk.CTkProgressBar(self._content)
        progress_bar.pack(fill="x", padx=20, pady=4)
        progress_bar.configure(mode="indeterminate")
        progress_bar.start()

        def do_install():
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True, text=True, timeout=120)
            return result.returncode == 0

        def on_success(success):
            progress_bar.stop()
            if success:
                if package in self._missing:
                    self._missing.remove(package)
                self._update_ui()
            else:
                progress_label.configure(
                    text=f"❌ Failed to install {package}",
                    text_color=colors["error"])

        def on_error(exc):
            progress_bar.stop()
            progress_label.configure(
                text=f"❌ Error: {exc}",
                text_color=colors["error"])

        thread_pool.run_in_thread(do_install, on_success, on_error)
