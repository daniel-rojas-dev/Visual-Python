"""
widget_factory.py — Widget palette and creation logic.
Each widget gets a mandatory unique Variable Name.
"""
import customtkinter as ctk
from config import WIDGET_TYPES, ThemeManager


class WidgetPalette(ctk.CTkFrame):
    """Left-side palette showing available widget types to drag onto canvas."""

    def __init__(self, parent, on_add_widget=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_add_widget = on_add_widget
        colors = ThemeManager.colors()
        self.configure(fg_color=colors["bg_secondary"], corner_radius=0)

        title = ctk.CTkLabel(self, text="🧩 Widgets",
                             font=("Segoe UI", 15, "bold"),
                             text_color=colors["fg_accent"])
        title.pack(padx=10, pady=(12, 6), anchor="w")

        sep = ctk.CTkFrame(self, height=1, fg_color=colors["border"])
        sep.pack(fill="x", padx=10, pady=(0, 8))

        for wt in WIDGET_TYPES:
            btn = ctk.CTkButton(
                self,
                text=f"  {wt['icon']}  {wt['display']}",
                anchor="w",
                font=("Segoe UI", 13),
                fg_color="transparent",
                hover_color=colors["selection"],
                text_color=colors["fg_text"],
                height=32,
                corner_radius=6,
                command=lambda t=wt["type"]: self._add(t),
            )
            btn.pack(fill="x", padx=8, pady=2)

    def _add(self, widget_type: str) -> None:
        if self._on_add_widget:
            self._on_add_widget(widget_type)


class ViewManager(ctk.CTkFrame):
    """Panel to manage views (screens) — add, delete, rename, switch."""

    def __init__(self, parent, canvas_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas_mgr = canvas_manager
        colors = ThemeManager.colors()
        self.configure(fg_color=colors["bg_secondary"], corner_radius=0)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(12, 6))

        ctk.CTkLabel(header, text="📱 Views",
                     font=("Segoe UI", 15, "bold"),
                     text_color=colors["fg_accent"]).pack(side="left")

        ctk.CTkButton(header, text="+", width=28, height=28,
                      font=("Segoe UI", 14, "bold"),
                      fg_color=colors["fg_accent"],
                      command=self._add_view).pack(side="right")
                      
        ctk.CTkButton(header, text="✏️", width=28, height=28,
                      font=("Segoe UI", 12),
                      fg_color=colors["bg_panel"],
                      command=self._rename_view).pack(side="right", padx=4)

        sep = ctk.CTkFrame(self, height=1, fg_color=colors["border"])
        sep.pack(fill="x", padx=10, pady=(0, 6))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=4)

        self.refresh()

    def refresh(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        colors = ThemeManager.colors()
        for name in list(self.canvas_mgr.views.keys()):
            is_current = (name == self.canvas_mgr.current_view)
            
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            
            btn = ctk.CTkButton(
                row,
                text=f"  {'▶' if is_current else '  '} {name}",
                anchor="w",
                font=("Segoe UI", 13, "bold" if is_current else "normal"),
                fg_color=colors["selection"] if is_current else "transparent",
                hover_color=colors["selection"],
                text_color=colors["fg_accent"] if is_current else colors["fg_text"],
                height=30,
                corner_radius=6,
                command=lambda n=name: self._switch(n),
            )
            btn.pack(side="left", fill="x", expand=True)

            if len(self.canvas_mgr.views) > 1:
                del_btn = ctk.CTkButton(
                    row, text="✖", width=28, height=30,
                    fg_color="transparent", hover_color=colors.get("error", "#cc0000"), text_color=colors["fg_text"],
                    command=lambda n=name: self._delete_view(n)
                )
                del_btn.pack(side="right", padx=(2, 0))

    def _delete_view(self, name: str) -> None:
        self.canvas_mgr.delete_view(name)
        self.refresh()

    def _add_view(self) -> None:
        idx = len(self.canvas_mgr.views) + 1
        name = f"View_{idx}"
        self.canvas_mgr.add_view(name)
        self.canvas_mgr.switch_view(name)
        self.refresh()

    def _switch(self, name: str) -> None:
        self.canvas_mgr.switch_view(name)
        self.refresh()

    def _rename_view(self) -> None:
        if not self.canvas_mgr.current_view: return
        dialog = ctk.CTkInputDialog(text="New name for view:", title="Rename View")
        new_name = dialog.get_input()
        if new_name and new_name != self.canvas_mgr.current_view and new_name not in self.canvas_mgr.views:
            old_name = self.canvas_mgr.current_view
            view_data = self.canvas_mgr.views.pop(old_name)
            view_data.name = new_name
            self.canvas_mgr.views[new_name] = view_data
            self.canvas_mgr.current_view = new_name
            self.refresh()
            self.canvas_mgr._trigger_change()
