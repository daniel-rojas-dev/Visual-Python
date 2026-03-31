"""
Visual Python IDE — Entry Point.
A low-resource IDE for rapid CustomTkinter development.
"""
import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import VisualPythonApp


def main():
    app = VisualPythonApp()
    app.after(100, lambda: app.state("zoomed"))
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
