"""
canvas_manager.py — Core engine for the visual canvas.
Supports relative coordinates, multiple views, absolute render, 
and Snap-to-Grid for low-resource environments.
"""
import customtkinter as ctk
import uuid
from typing import Dict, Optional, Callable
from config import ThemeManager


class ViewData:
    """Stores structured data for a single screen/view."""
    def __init__(self, name: str, scrollable: bool = False):
        self.name = name
        self.scrollable = scrollable
        self.bg_color = ""
        self.widgets: Dict[str, dict] = {}
        self.anchor_sections = {
            "header": False,
            "footer": False,
            "sidebar": False
        }


class CanvasManager:
    """Manages widgets on a relative-coordinate canvas."""

    def __init__(self, canvas_frame: ctk.CTkFrame, on_widget_deleted: Callable = None, on_widget_renamed: Callable = None):
        self.canvas_frame = canvas_frame
        self.on_widget_deleted = on_widget_deleted
        self.on_widget_renamed = on_widget_renamed
        self.global_bg_color = "#1a1a2e"
        self.project_geometry = "800x600"
        
        self.views: Dict[str, ViewData] = {"Main": ViewData("Main")}
        self.current_view = "Main"
        self.selected_widget: Optional[str] = None
        self.project_variables: Dict[str, str] = {}
        
        self._live_widgets: Dict[str, ctk.CTkBaseClass] = {}
        self._on_changed_callback: Optional[Callable] = None
        self._on_selection_changed: Optional[Callable] = None
        self._on_show_variables_requested: Optional[Callable] = None
        self._drag_data = {}
        self.snap_grid = 1.0 / 12.0  # 12x12 grid. Set to 0 to disable

    def add_view(self, name: str, scrollable: bool = False) -> None:
        if name not in self.views:
            self.views[name] = ViewData(name, scrollable)

    def delete_view(self, name: str) -> None:
        if name in self.views and len(self.views) > 1:
            del self.views[name]
            if self.current_view == name:
                self.switch_view(list(self.views.keys())[0])
            self._trigger_change()

    def switch_view(self, name: str) -> None:
        if name in self.views:
            self.current_view = name
            self.selected_widget = None
            self._render_view()

    def add_widget(self, widget_type: str, rx=0.5, ry=0.5, var_name=None, props=None) -> str:
        """Add a widget using normalized coordinates (0.0 - 1.0)."""
        if not self.current_view: return ""
        view = self.views[self.current_view]
        
        # Auto-name
        if not var_name:
            base = widget_type.replace("CTk", "").lower()
            count = sum(1 for v in self.views.values() for w in v.widgets.values() if w["type"] == widget_type) + 1
            var_name = f"{base}_{count}"
            
        # Ensure unique globally across all views
        all_names = set(n for v in self.views.values() for n in v.widgets.keys())
        while var_name in all_names:
            var_name = f"{var_name}_{uuid.uuid4().hex[:4]}"
            all_names.add(var_name)

        widget_data = {
            "type": widget_type,
            "rx": max(0.0, min(1.0, rx)),
            "ry": max(0.0, min(1.0, ry)),
            "rw": 0.2,
            "rh": 0.06,
            "props": props or self._default_props(widget_type),
        }
        view.widgets[var_name] = widget_data
        self._render_view()
        self._trigger_change()
        return var_name

    def rename_widget(self, old_name: str, new_name: str) -> str:
        if not self.current_view or not new_name: return old_name
        view = self.views[self.current_view]
        all_names = set(n for v in self.views.values() for n in v.widgets.keys())
        if old_name in view.widgets and new_name not in all_names:
            if not new_name.isidentifier(): return old_name
            view.widgets[new_name] = view.widgets.pop(old_name)
            if self.selected_widget == old_name: self.selected_widget = new_name
            if self.on_widget_renamed: self.on_widget_renamed(old_name, new_name)
            self._render_view()
            self._trigger_change()
            return new_name
        return old_name

    def delete_widget(self, var_name: str) -> None:
        if not self.current_view: return
        view = self.views[self.current_view]
        if var_name in view.widgets:
            del view.widgets[var_name]
            if self.on_widget_deleted: self.on_widget_deleted(var_name)
            if self.selected_widget == var_name: self.selected_widget = None
            self._render_view()
            self._trigger_change()

    def update_widget_props(self, var_name: str, props: dict) -> None:
        if not self.current_view: return
        view = self.views[self.current_view]
        if var_name in view.widgets:
            view.widgets[var_name]["props"].update(props)
            live_w = self._live_widgets.get(var_name)
            if live_w:
                safe_props = {k: v for k, v in props.items() if k not in ("width", "height")}
                if safe_props:
                    try: live_w.configure(**safe_props)
                    except: self._render_view()
            else: self._render_view()
            self._trigger_change()

    def select_widget(self, var_name: str | None) -> None:
        self.selected_widget = var_name
        self._render_view()

    # ─── Rendering ────────────────────────────────────────────────
    def _render_view(self) -> None:
        # Destroy ONLY widgets. Avoid flickering by not clearing everything if possible, 
        # but CTk requires fresh instantiation for parent change or deep prop swap.
        for w in self._live_widgets.values():
            try: w.destroy()
            except: pass
        self._live_widgets.clear()
        
        # Ensure frame is clean
        for child in self.canvas_frame.winfo_children():
            try: child.destroy()
            except: pass

        if not self.current_view or self.current_view not in self.views: return
        view = self.views[self.current_view]
        bg = view.bg_color or self.global_bg_color
        self.canvas_frame.configure(fg_color=bg)

        self.canvas_frame.update_idletasks()
        cw = max(self.canvas_frame.winfo_width(), 400)
        ch = max(self.canvas_frame.winfo_height(), 300)
        
        self.canvas_frame.bind("<Button-1>", self._on_bg_click)

        # Draw grid
        if self.snap_grid > 0:
            grid_color = ThemeManager.colors()["border"]
            for i in range(1, 12):
                # Horizontal lines
                hline = ctk.CTkFrame(self.canvas_frame, height=1, fg_color=grid_color, corner_radius=0)
                hline.place(x=0, rely=i/12.0, relwidth=1.0)
                
                # Vertical lines
                vline = ctk.CTkFrame(self.canvas_frame, width=1, fg_color=grid_color, corner_radius=0)
                vline.place(relx=i/12.0, y=0, relheight=1.0)

        for var_name, wdata in view.widgets.items():
            widget = self._create_live_widget(var_name, wdata, cw, ch)
            if widget: self._live_widgets[var_name] = widget

    def _create_live_widget(self, var_name: str, wdata: dict, canvas_w: int, canvas_h: int):
        wtype = wdata["type"]
        props = wdata["props"]
        ax, ay = int(wdata["rx"] * canvas_w), int(wdata["ry"] * canvas_h)
        aw, ah = int(wdata["rw"] * canvas_w), int(wdata["rh"] * canvas_h)

        try:
            kwargs = {"width": aw, "height": ah}
            if wtype == "CTkLabel":
                if props.get("text"): kwargs["text"] = props["text"]
                if props.get("text_color"): kwargs["text_color"] = props["text_color"]
                if props.get("fg_color"): kwargs["fg_color"] = props["fg_color"]
                widget = ctk.CTkLabel(self.canvas_frame, **kwargs)
            elif wtype == "CTkButton":
                if props.get("text"): kwargs["text"] = props["text"]
                if props.get("fg_color"): kwargs["fg_color"] = props["fg_color"]
                if props.get("text_color"): kwargs["text_color"] = props["text_color"]
                if props.get("hover_color"): kwargs["hover_color"] = props["hover_color"]
                widget = ctk.CTkButton(self.canvas_frame, **kwargs)
            elif wtype in ("CTkEntry", "CTkEntryNum"):
                if props.get("placeholder"): kwargs["placeholder_text"] = props["placeholder"]
                if props.get("text_color"): kwargs["text_color"] = props["text_color"]
                if props.get("fg_color"): kwargs["fg_color"] = props["fg_color"]
                widget = ctk.CTkEntry(self.canvas_frame, **kwargs)
            else:
                widget = ctk.CTkLabel(self.canvas_frame, text=f"[{wtype}]")
        except Exception as e:
            print(f"Widget error: {e}")
            widget = ctk.CTkLabel(self.canvas_frame, text=f"Error {wtype}")

        if widget:
            widget.place(x=ax, y=ay)
            if var_name == self.selected_widget:
                try: widget.configure(border_width=2, border_color="#00ffff")
                except: pass
            
            # Setup Bindings
            # Use root events for drag to avoid coordinate jitter
            widget.bind("<Button-1>", lambda e, vn=var_name: self._on_click(vn, e))
            widget.bind("<B1-Motion>", lambda e, vn=var_name: self._on_drag(vn, e))
            widget.bind("<ButtonRelease-1>", lambda e, vn=var_name: self._on_drop(vn, e))
        return widget

    # ─── Interactions ─────────────────────────────────────────────
    def _on_click(self, var_name: str, event) -> None:
        if self.selected_widget != var_name:
            self.selected_widget = var_name
            # Instead of full render, just highlight the widget for speed and focus
            for vn, w in self._live_widgets.items():
                if hasattr(w, 'configure'):
                    try:
                        if vn == var_name: w.configure(border_width=2, border_color="#00ffff")
                        else: w.configure(border_width=0)
                    except: pass
        
        view = self.views.get(self.current_view)
        start_rx = view.widgets[var_name]["rx"] if view and var_name in view.widgets else 0.5
        start_ry = view.widgets[var_name]["ry"] if view and var_name in view.widgets else 0.5
        
        self._drag_data = {
            "start_x": event.x_root, 
            "start_y": event.y_root,
            "start_rx": start_rx,
            "start_ry": start_ry
        }
        if self._on_selection_changed:
            self._on_selection_changed(var_name)
            
    def _on_bg_click(self, event) -> None:
        self.selected_widget = None
        for vn, w in self._live_widgets.items():
            if hasattr(w, 'configure'):
                try: w.configure(border_width=0)
                except: pass
        if self._on_selection_changed:
            self._on_selection_changed(None)


    def _on_drag(self, var_name: str, event) -> None:
        if not self._drag_data: return
        view = self.views.get(self.current_view)
        if not view or var_name not in view.widgets: return
        
        cw = max(self.canvas_frame.winfo_width(), 1)
        ch = max(self.canvas_frame.winfo_height(), 1)
        
        dx = (event.x_root - self._drag_data["start_x"]) / cw
        dy = (event.y_root - self._drag_data["start_y"]) / ch
        
        wdata = view.widgets[var_name]
        raw_rx = self._drag_data["start_rx"] + dx
        raw_ry = self._drag_data["start_ry"] + dy
        
        if self.snap_grid > 0:
            snapped_rx = round(raw_rx / self.snap_grid) * self.snap_grid
            snapped_ry = round(raw_ry / self.snap_grid) * self.snap_grid
        else:
            snapped_rx = raw_rx
            snapped_ry = raw_ry
            
        wdata["rx"] = max(0.0, min(1.0, snapped_rx))
        wdata["ry"] = max(0.0, min(1.0, snapped_ry))
        
        # Note: Do not update start_x or start_y here, 
        # so cumulative fractional mouse movements are not lost!
        
        # Update live position
        live_w = self._live_widgets.get(var_name)
        if live_w:
            live_w.place(x=int(wdata["rx"] * cw), y=int(wdata["ry"] * ch))

    def _on_drop(self, var_name: str, event) -> None:
        self._drag_data = {}
        self._trigger_change()

    def _trigger_change(self) -> None:
        if self._on_changed_callback: self._on_changed_callback()

    def set_on_changed_callback(self, callback) -> None:
        self._on_changed_callback = callback

    def set_selection_callback(self, callback) -> None:
        self._on_selection_changed = callback

    def set_show_variables_callback(self, callback) -> None:
        self._on_show_variables_requested = callback

    def _default_props(self, widget_type: str) -> dict:
        defaults = {
            "CTkLabel": {"text": "Label", "text_color": "", "fg_color": "transparent"},
            "CTkButton": {"text": "Button", "fg_color": "", "text_color": "", "hover_color": ""},
            "CTkEntry": {"placeholder": "Enter text...", "text_color": "", "fg_color": "", "variable_key": ""},
            "CTkEntryNum": {"placeholder": "Enter number...", "text_color": "", "fg_color": "", "variable_key": ""},
        }
        return defaults.get(widget_type, {}).copy()

    def to_dict(self) -> dict:
        return {"global_bg_color": self.global_bg_color, 
                "project_geometry": self.project_geometry,
                "project_variables": self.project_variables,
                "current_view": self.current_view,
                "views": {n: {"name": v.name, "scrollable": v.scrollable, "bg_color": v.bg_color,
                             "widgets": v.widgets, "anchor_sections": v.anchor_sections}
                         for n, v in self.views.items()}}

    def from_dict(self, data: dict) -> None:
        self.global_bg_color = data.get("global_bg_color", "#1a1a2e")
        self.project_geometry = data.get("project_geometry", "800x600")
        self.project_variables = data.get("project_variables", {})
        self.views.clear()
        for name, vdata in data.get("views", {}).items():
            view = ViewData(vdata["name"], vdata.get("scrollable", False))
            view.bg_color = vdata.get("bg_color", "")
            view.widgets = vdata.get("widgets", {})
            self.views[name] = view
        cv = data.get("current_view", "")
        if cv in self.views: self.switch_view(cv)
        elif self.views: self.switch_view(list(self.views.keys())[0])
