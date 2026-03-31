"""
app.py — Main IDE application class.
Assembles all components: Canvas, Properties, Node Editor, Code Editor,
Widget Palette, View Manager, Preview, and Auto-Importer.
Optimized: Uses threading for all heavy ops; lightweight layout via grid.
"""
import customtkinter as ctk
import json
import os
from tkinter import filedialog, messagebox

from config import (
    DEFAULT_GEOMETRY, MIN_WIDTH, MIN_HEIGHT,
    ThemeManager, PROJECT_EXTENSION
)
from canvas.canvas_manager import CanvasManager
from canvas.widget_factory import WidgetPalette, ViewManager
from canvas.property_panel import PropertyPanel
from nodes.node_engine import NodeEngine
from nodes.node_canvas import NodeCanvas
from codegen.code_generator import CodeGenerator
from codegen.code_parser import CodeParser
from ide.code_editor import CodeEditor
from compiler.exporter import Exporter
from compiler.preview import PreviewWindow, PreviewPanel
from utils.threading_utils import thread_pool
from utils.history_stack import HistoryStack


class VisualPythonApp(ctk.CTk):
    """Main IDE window — assembles all panels and manages state."""

    def __init__(self):
        super().__init__()

        # ─── Window Setup ─────────────────────────────────────────
        self.title("Visual Python IDE")
        self.geometry(DEFAULT_GEOMETRY)
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.state("zoomed")
        ThemeManager.set_mode("dark")

        # ─── Core Objects ─────────────────────────────────────────
        self.node_engine = NodeEngine()
        self.code_generator = CodeGenerator()
        self.code_parser = CodeParser()
        self.preview = PreviewWindow()
        self.history = HistoryStack(max_size=6)
        self._project_path: str = ""
        self.needs_sync: bool = False

        # ─── Layout Grid ──────────────────────────────────────────
        # Row 0: toolbar
        # Row 1: main content (expandable)
        # Row 2: bottom panel (code/nodes)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ─── Top Toolbar ──────────────────────────────────────────
        self._create_toolbar()

        # ─── Left Panel (Palette + Views) ─────────────────────────
        left_panel = ctk.CTkFrame(self, width=200, corner_radius=0,
                                  fg_color=ThemeManager.colors()["bg_secondary"])
        left_panel.grid(row=1, column=0, sticky="nsw", rowspan=2)
        left_panel.grid_propagate(False)
        left_panel.configure(width=200)

        # Canvas area (center)
        canvas_frame = ctk.CTkFrame(self, corner_radius=0,
                                    fg_color=ThemeManager.colors()["bg_canvas"])
        canvas_frame.grid(row=1, column=1, sticky="nsew")

        self.canvas_mgr = CanvasManager(
            canvas_frame,
            on_widget_deleted=self._on_widget_deleted,
            on_widget_renamed=self._on_widget_renamed)
        self.canvas_mgr.set_on_changed_callback(self._on_canvas_changed)

        # Widget palette
        self.palette = WidgetPalette(left_panel,
                                     on_add_widget=self._add_widget_to_canvas)
        self.palette.pack(fill="x")

        # View manager
        self.view_mgr = ViewManager(left_panel, self.canvas_mgr)
        self.view_mgr.pack(fill="both", expand=True, pady=(8, 0))

        # ─── Right Panel (Properties + Build) ─────────────────────
        right_panel = ctk.CTkFrame(self, width=240, corner_radius=0,
                                   fg_color=ThemeManager.colors()["bg_secondary"])
        right_panel.grid(row=1, column=2, sticky="nse", rowspan=2)
        right_panel.grid_propagate(False)
        right_panel.configure(width=240)

        self.property_panel = PropertyPanel(right_panel, self.canvas_mgr,
                                            node_engine=self.node_engine)
        self.property_panel.pack(fill="both", expand=True)

        # Build panel
        self.preview_panel = PreviewPanel(
            right_panel,
            on_preview=self._do_preview,
            on_compile=self._do_compile,
            on_export_py=self._do_export_py)
        self.preview_panel.pack(fill="x", pady=(8, 0))



        # ─── Bottom Panel (Tabview: Nodes / Code) ─────────────────
        bottom_frame = ctk.CTkFrame(self, height=280, corner_radius=0,
                                    fg_color=ThemeManager.colors()["bg_primary"])
        bottom_frame.grid(row=2, column=1, sticky="nsew")
        bottom_frame.grid_propagate(False)
        bottom_frame.configure(height=280)

        self.bottom_tabs = ctk.CTkTabview(
            bottom_frame,
            fg_color=ThemeManager.colors()["bg_primary"],
            segmented_button_fg_color=ThemeManager.colors()["bg_secondary"],
            segmented_button_selected_color=ThemeManager.colors()["fg_accent"],
            corner_radius=0)
        self.bottom_tabs.pack(fill="both", expand=True)

        # Node Editor tab
        node_tab = self.bottom_tabs.add("🔗 Nodes")
        self.node_canvas = NodeCanvas(node_tab, self.node_engine,
                                      canvas_manager=self.canvas_mgr)
        self.node_canvas.pack(fill="both", expand=True)
        self.node_canvas.set_on_node_selected(self.property_panel._on_node_selection_changed)
        self.property_panel.node_canvas = self.node_canvas

        # Code Editor tab
        code_tab = self.bottom_tabs.add("📝 Code")
        self.code_editor = CodeEditor(code_tab,
                                      on_refresh=self._do_refresh)
        self.code_editor.pack(fill="both", expand=True)

        # ─── Keyboard Shortcuts ───────────────────────────────────
        self.bind("<Control-s>", lambda e: self._save_project())
        self.bind("<Control-o>", lambda e: self._open_project())
        self.bind("<Control-n>", lambda e: self._new_project())
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())
        self.bind("<Control-r>", lambda e: self._do_refresh())
        self.bind("<F5>", lambda e: self._do_preview())

        # ─── Thread result processor ──────────────────────────────
        thread_pool.process_results(self)

        # ─── Initial state ────────────────────────────────────────
        self._push_history()
        self._generate_code()

    # ─── Toolbar ──────────────────────────────────────────────────
    def _create_toolbar(self) -> None:
        colors = ThemeManager.colors()
        toolbar = ctk.CTkFrame(self, height=40, corner_radius=0,
                               fg_color=colors["bg_secondary"])
        toolbar.grid(row=0, column=0, columnspan=3, sticky="ew")
        toolbar.grid_propagate(False)

        # Logo
        ctk.CTkLabel(toolbar, text="🐍 Visual Python",
                     font=("Segoe UI", 16, "bold"),
                     text_color=colors["fg_accent"]).pack(side="left", padx=12)

        # File buttons
        for text, cmd in [
            ("📁 New", self._new_project),
            ("📂 Open", self._open_project),
            ("💾 Save", self._save_project),
        ]:
            ctk.CTkButton(toolbar, text=text, width=70, height=28,
                          font=("Segoe UI", 11),
                          fg_color="transparent",
                          hover_color=colors["selection"],
                          text_color=colors["fg_text"],
                          corner_radius=4,
                          command=cmd).pack(side="left", padx=2, pady=6)

        # Separator
        ctk.CTkFrame(toolbar, width=1, height=24,
                     fg_color=colors["border"]).pack(side="left", padx=8, pady=8)

        # Undo / Redo
        ctk.CTkButton(toolbar, text="↩ Undo", width=60, height=28,
                      font=("Segoe UI", 11),
                      fg_color="transparent",
                      hover_color=colors["selection"],
                      text_color=colors["fg_text"],
                      command=self._undo).pack(side="left", padx=2, pady=6)
        ctk.CTkButton(toolbar, text="↪ Redo", width=60, height=28,
                      font=("Segoe UI", 11),
                      fg_color="transparent",
                      hover_color=colors["selection"],
                      text_color=colors["fg_text"],
                      command=self._redo).pack(side="left", padx=2, pady=6)



    # ─── Widget Actions ───────────────────────────────────────────
    def _add_widget_to_canvas(self, widget_type: str) -> None:
        var_name = self.canvas_mgr.add_widget(widget_type)
        if var_name:
            self.canvas_mgr.select_widget(var_name)
            # No real-time sync anymore:
            self._on_canvas_changed()

    def _on_canvas_changed(self) -> None:
        """Mark as dirty when canvas updates."""
        self.needs_sync = True
        self.code_editor.set_dirty(True)
        self._push_history()

    def _on_widget_deleted(self, var_name: str) -> None:
        """Orphan GC: clean up nodes linked to deleted widget."""
        removed = self.node_engine.gc_remove_by_var_name(var_name)
        if removed > 0:
            self.node_canvas.redraw_all()

    def _on_widget_renamed(self, old_name: str, new_name: str) -> None:
        """Update node logic references when a widget changes name."""
        updated = self.node_engine.update_var_name(old_name, new_name)
        if updated > 0:
            self.node_canvas.redraw_all()

    def _generate_code(self) -> None:
        canvas_data = self.canvas_mgr.to_dict()
        node_data = self.node_engine.to_dict()
        user_code = self.code_parser.extract_user_code(
            self.code_editor.get_code())
        code = self.code_generator.generate(
            canvas_data, node_data,
            ThemeManager.get_mode(), user_code)
        self.code_editor.set_code(code)

    def _do_refresh(self) -> None:
        """Bidirectional sync: Code ↔ Canvas."""
        code = self.code_editor.get_code()

        # 1. Full Syntax Check
        ok, err = self.code_parser.validate_syntax(code)
        if not ok:
            messagebox.showwarning("Syntax Error", 
                                   f"{err}\n\nRevisa el código antes de actualizar.")
            return

        # 2. Region Check
        valid, error = self.code_parser.validate_region(code)
        if not valid:
            messagebox.showwarning("Refresh Error",
                                   f"Cannot sync — {error}\n\n"
                                   "Fix the ui_data dict and try again.")
            return

        # 3. Update canvas from code
        self.code_parser.update_canvas_from_code(code, self.canvas_mgr)
        self.view_mgr.refresh()

        # 4. Regenerate code from updated canvas
        self._generate_code()
        self._push_history()
        
        # Reset dirty state
        self.needs_sync = False
        self.code_editor.set_dirty(False)

    # ─── Preview & Compile ────────────────────────────────────────
    def _do_preview(self) -> None:
        self._generate_code()
        code = self.code_editor.get_code()
        self.preview_panel.set_status("▶️ Preview running...")
        self.preview.start(code,
                          on_error=lambda msg: self.preview_panel.set_status(
                              f"❌ {msg[:100]}"))

    def _do_export_py(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py")],
            title="Export Python File")
        if not path:
            return
        self._generate_code()
        code = self.code_editor.get_code()
        ok, msg = Exporter.export_py(code, path)
        self.preview_panel.set_status(f"{'✅' if ok else '❌'} {msg}")

    def _do_compile(self) -> None:
        if not Exporter.check_pyinstaller():
            messagebox.showinfo(
                "PyInstaller Required",
                "PyInstaller is not installed.\n\n"
                "Install it with: pip install pyinstaller")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py")],
            title="Save .py before compiling")
        if not path:
            return

        self._generate_code()
        code = self.code_editor.get_code()
        ok, msg = Exporter.export_py(code, path)
        if not ok:
            self.preview_panel.set_status(f"❌ {msg}")
            return

        self.preview_panel.set_status("⏳ Compiling .exe...")
        Exporter.export_exe(
            path,
            output_dir=os.path.dirname(path),
            on_progress=lambda line: None,
            on_complete=lambda exe: self.preview_panel.set_status(
                f"✅ Built: {os.path.basename(exe)}"),
            on_error=lambda err: self.preview_panel.set_status(
                f"❌ Build failed"))

    # ─── Theme ────────────────────────────────────────────────────
    def _change_theme(self, mode: str) -> None:
        ThemeManager.set_mode(mode.lower())
        self._on_canvas_changed()

    # ─── Undo / Redo ──────────────────────────────────────────────
    def _push_history(self) -> None:
        state = {
            "canvas": self.canvas_mgr.to_dict(),
            "nodes": self.node_engine.to_dict(),
        }
        self.history.push(state)

    def _undo(self) -> None:
        state = self.history.undo()
        if state:
            self._restore_state(state)

    def _redo(self) -> None:
        state = self.history.redo()
        if state:
            self._restore_state(state)

    def _restore_state(self, state: dict) -> None:
        self.canvas_mgr.from_dict(state.get("canvas", {}))
        self.node_engine.from_dict(state.get("nodes", {}))
        self.view_mgr.refresh()
        self.node_canvas.redraw_all()
        self._generate_code()
        self.needs_sync = False
        self.code_editor.set_dirty(False)

    # ─── Project Save / Load (.vpy) ───────────────────────────────
    def _new_project(self) -> None:
        if messagebox.askyesno("New Project",
                                "Discard current project?"):
            self.canvas_mgr.views.clear()
            self.canvas_mgr.add_view("Main")
            self.canvas_mgr.switch_view("Main")
            self.node_engine.clear()
            self.view_mgr.refresh()
            self.node_canvas.redraw_all()
            self.history.clear()
            self._project_path = ""
            self._push_history()
            self._generate_code()

    def _save_project(self) -> None:
        if not self._project_path:
            path = filedialog.asksaveasfilename(
                defaultextension=PROJECT_EXTENSION,
                filetypes=[("Visual Python Project", f"*{PROJECT_EXTENSION}")],
                title="Save Project")
            if not path:
                return
            self._project_path = path

        project_data = {
            "version": "1.0",
            "theme": ThemeManager.get_mode(),
            "canvas": self.canvas_mgr.to_dict(),
            "nodes": self.node_engine.to_dict(),
            "user_code": self.code_parser.extract_user_code(
                self.code_editor.get_code()),
        }
        try:
            with open(self._project_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            self.preview_panel.set_status(
                f"💾 Saved: {os.path.basename(self._project_path)}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def _open_project(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Visual Python Project", f"*{PROJECT_EXTENSION}"),
                       ("All files", "*.*")],
            title="Open Project")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._project_path = path
            ThemeManager.set_mode(data.get("theme", "dark"))
            self.canvas_mgr.from_dict(data.get("canvas", {}))
            self.node_engine.from_dict(data.get("nodes", {}))
            self.view_mgr.refresh()
            self.node_canvas.redraw_all()
            self.history.clear()
            self._push_history()
            self._generate_code()

            # Inject user code if present
            user_code = data.get("user_code", "")
            if user_code:
                current_code = self.code_editor.get_code()
                # Regenerate with user code
                canvas_data = self.canvas_mgr.to_dict()
                node_data = self.node_engine.to_dict()
                code = self.code_generator.generate(
                    canvas_data, node_data,
                    ThemeManager.get_mode(), user_code)
                self.code_editor.set_code(code)

            self.preview_panel.set_status(
                f"📂 Opened: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Open Error", str(e))

    # ─── Cleanup ──────────────────────────────────────────────────
    def on_closing(self) -> None:
        self.preview.stop()
        self.destroy()
