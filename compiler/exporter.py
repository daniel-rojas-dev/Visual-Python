"""
exporter.py — Export to .py file and .exe via PyInstaller.
All heavy operations run in background threads.
"""
import os
import subprocess
import sys
from utils.threading_utils import thread_pool


class Exporter:
    """Handles exporting the generated code to .py and .exe."""

    @staticmethod
    def export_py(code: str, filepath: str) -> tuple[bool, str]:
        """
        Write generated code to a .py file.
        Returns (success, message).
        """
        try:
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            return True, f"Exported to {filepath}"
        except Exception as e:
            return False, f"Export failed: {e}"

    @staticmethod
    def export_exe(py_filepath: str, output_dir: str = None,
                   on_progress=None, on_complete=None,
                   on_error=None, app_name: str = "MyApp") -> None:
        """
        Run PyInstaller in a background thread.
        `on_progress(line)` — called for each output line.
        `on_complete(exe_path)` — called when done.
        `on_error(error_msg)` — called on failure.
        """
        if output_dir is None:
            output_dir = os.path.dirname(py_filepath)

        def do_build():
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile",
                "--windowed",
                f"--name={app_name}",
                f"--distpath={output_dir}",
                f"--workpath={os.path.join(output_dir, 'build_temp')}",
                f"--specpath={os.path.join(output_dir, 'build_temp')}",
                py_filepath,
            ]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)
            
            output_lines = []
            for line in process.stdout:
                line = line.strip()
                output_lines.append(line)
                if on_progress:
                    on_progress(line)
            
            process.wait()
            
            if process.returncode == 0:
                exe_path = os.path.join(output_dir, f"{app_name}.exe")
                return ("success", exe_path)
            else:
                return ("error", "\n".join(output_lines[-10:]))

        def on_result(result):
            status, data = result
            if status == "success" and on_complete:
                on_complete(data)
            elif status == "error" and on_error:
                on_error(data)

        def on_exc(exc):
            if on_error:
                on_error(str(exc))

        thread_pool.run_in_thread(do_build, on_result, on_exc)

    @staticmethod
    def check_pyinstaller() -> bool:
        """Check if PyInstaller is installed."""
        try:
            import PyInstaller  # noqa
            return True
        except ImportError:
            return False
