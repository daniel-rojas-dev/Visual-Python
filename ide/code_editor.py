"""
code_editor.py — Syntax-highlighted code panel.
Optimized: Lazy highlighting — processes only visible lines.
"""
import customtkinter as ctk
import re
import keyword
from config import ThemeManager, FONT_CODE


# Syntax highlight patterns (compiled once at module load)
_KW_PATTERN = re.compile(
    r'\b(' + '|'.join(keyword.kwlist) + r')\b')
_BUILTIN_PATTERN = re.compile(
    r'\b(print|len|range|int|str|float|list|dict|set|tuple|True|False|None'
    r'|self|super|isinstance|hasattr|getattr|setattr)\b')
_STRING_PATTERN = re.compile(r'(\".*?\"|\'.*?\'|f\".*?\"|f\'.*?\')')
_COMMENT_PATTERN = re.compile(r'(#.*$)', re.MULTILINE)
_DECORATOR_PATTERN = re.compile(r'(@\w+)')
_NUMBER_PATTERN = re.compile(r'\b(\d+\.?\d*)\b')

# Colors for dark theme
HIGHLIGHT_COLORS = {
    "keyword":   "#c678dd",
    "builtin":   "#e5c07b",
    "string":    "#98c379",
    "comment":   "#5c6370",
    "decorator": "#61afef",
    "number":    "#d19a66",
    "normal":    "#abb2bf",
}


class CodeEditor(ctk.CTkFrame):
    """Syntax-highlighted code editor with lazy highlighting."""

    def __init__(self, parent, on_refresh=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_refresh = on_refresh
        colors = ThemeManager.colors()
        self.configure(fg_color=colors["bg_primary"], corner_radius=0)

        # Toolbar
        toolbar = ctk.CTkFrame(self, height=36, fg_color=colors["bg_secondary"],
                               corner_radius=0)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        ctk.CTkLabel(toolbar, text="📝 Code Editor",
                     font=("Segoe UI", 13, "bold"),
                     text_color=colors["fg_accent"]).pack(side="left", padx=10)

        self.btn_refresh = ctk.CTkButton(
            toolbar, text="🔄 Refresh", height=26, width=90,
            font=("Segoe UI", 11, "bold"),
            fg_color=colors["fg_accent"],
            hover_color=colors["fg_accent2"],
            corner_radius=4,
            command=self._do_refresh)
        self.btn_refresh.pack(side="right", padx=8, pady=5)

        ctk.CTkButton(toolbar, text="📋 Copy", height=26, width=70,
                      font=("Segoe UI", 11),
                      fg_color=colors["bg_panel"],
                      corner_radius=4,
                      command=self._copy_all).pack(side="right", padx=4, pady=5)

        # Editor area with line numbers
        editor_frame = ctk.CTkFrame(self, fg_color="transparent")
        editor_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Line number column
        self.line_numbers = ctk.CTkTextbox(
            editor_frame, width=45, font=(FONT_CODE, 11),
            fg_color=colors["bg_secondary"],
            text_color="#666666",
            state="disabled",
            activate_scrollbars=False)
        self.line_numbers.pack(side="left", fill="y")

        # Main code textbox
        self.textbox = ctk.CTkTextbox(
            editor_frame, font=(FONT_CODE, 12),
            fg_color=colors["bg_primary"],
            text_color=HIGHLIGHT_COLORS["normal"],
            wrap="none",
            undo=True)
        self.textbox.pack(side="left", fill="both", expand=True)

        # Status bar
        self.status = ctk.CTkLabel(
            self, text="Ready", height=22,
            font=("Segoe UI", 10),
            text_color="#808080",
            fg_color=colors["bg_secondary"],
            anchor="w")
        self.status.pack(fill="x", padx=0)

        # Bind events for lazy highlighting
        self.textbox.bind("<KeyRelease>", self._on_key_release)
        self.textbox.bind("<MouseWheel>", self._schedule_highlight)
        self._highlight_job = None
        self._last_visible_range = (0, 0)

        # Configure highlight tags
        for tag, color in HIGHLIGHT_COLORS.items():
            self.textbox.tag_config(tag, foreground=color)

    def set_code(self, code: str) -> None:
        """Set the editor content."""
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", code)
        self._update_line_numbers()
        self._highlight_visible()

    def get_code(self) -> str:
        """Get the editor content."""
        return self.textbox.get("1.0", "end-1c")

    # ─── Lazy Syntax Highlighting ─────────────────────────────────
    def _on_key_release(self, event=None) -> None:
        self._update_line_numbers()
        self._schedule_highlight()

    def _schedule_highlight(self, event=None) -> None:
        """Debounce: highlight only after 150ms of inactivity."""
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(150, self._highlight_visible)

    def _highlight_visible(self) -> None:
        """Only highlight lines currently visible on screen (lazy)."""
        try:
            # Get visible range
            first_visible = self.textbox.index("@0,0")
            last_visible = self.textbox.index(f"@0,{self.textbox.winfo_height()}")
            first_line = int(first_visible.split(".")[0])
            last_line = int(last_visible.split(".")[0]) + 1

            # Skip if same range (optimization)
            if (first_line, last_line) == self._last_visible_range:
                return
            self._last_visible_range = (first_line, last_line)

            # Clear existing tags in range
            start_idx = f"{first_line}.0"
            end_idx = f"{last_line}.end"
            for tag in HIGHLIGHT_COLORS:
                self.textbox.tag_remove(tag, start_idx, end_idx)

            # Get visible text
            visible_text = self.textbox.get(start_idx, end_idx)

            # Apply patterns only to visible lines
            for i, line in enumerate(visible_text.split("\n")):
                line_num = first_line + i
                line_start = f"{line_num}.0"

                # Comments first (highest priority)
                for m in _COMMENT_PATTERN.finditer(line):
                    s = f"{line_num}.{m.start()}"
                    e = f"{line_num}.{m.end()}"
                    self.textbox.tag_add("comment", s, e)

                # Strings
                for m in _STRING_PATTERN.finditer(line):
                    s = f"{line_num}.{m.start()}"
                    e = f"{line_num}.{m.end()}"
                    self.textbox.tag_add("string", s, e)

                # Keywords
                for m in _KW_PATTERN.finditer(line):
                    s = f"{line_num}.{m.start()}"
                    e = f"{line_num}.{m.end()}"
                    self.textbox.tag_add("keyword", s, e)

                # Builtins
                for m in _BUILTIN_PATTERN.finditer(line):
                    s = f"{line_num}.{m.start()}"
                    e = f"{line_num}.{m.end()}"
                    self.textbox.tag_add("builtin", s, e)

                # Decorators
                for m in _DECORATOR_PATTERN.finditer(line):
                    s = f"{line_num}.{m.start()}"
                    e = f"{line_num}.{m.end()}"
                    self.textbox.tag_add("decorator", s, e)

                # Numbers
                for m in _NUMBER_PATTERN.finditer(line):
                    s = f"{line_num}.{m.start()}"
                    e = f"{line_num}.{m.end()}"
                    self.textbox.tag_add("number", s, e)

        except Exception:
            pass  # Don't crash the IDE on highlight errors

    def _update_line_numbers(self) -> None:
        """Update line number column."""
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", "end")
        text = self.textbox.get("1.0", "end-1c")
        line_count = text.count("\n") + 1
        numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert("1.0", numbers)
        self.line_numbers.configure(state="disabled")

    # ─── Actions ──────────────────────────────────────────────────
    def _do_refresh(self) -> None:
        """Trigger bidirectional sync."""
        if self._on_refresh:
            self._on_refresh()

    def set_dirty(self, is_dirty: bool) -> None:
        """Update Refresh button color to indicate sync needed."""
        colors = ThemeManager.colors()
        if is_dirty:
            self.btn_refresh.configure(
                fg_color="#e67e22",  # Orange for 'dirty'
                text="🔄 Refresh*")
            self.status.configure(text="⚠️ Canvas changed — Refresh needed to update code")
        else:
            self.btn_refresh.configure(
                fg_color=colors["fg_accent"],
                text="🔄 Refresh")
            self.status.configure(text="✅ Refreshed — Canvas ↔ Code synced")

    def _copy_all(self) -> None:
        code = self.get_code()
        self.clipboard_clear()
        self.clipboard_append(code)
        self.status.configure(text="📋 Code copied to clipboard")
