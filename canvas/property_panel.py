"""
property_panel.py — Widget and Node property inspector (right panel).
Includes "Connect to..." field and node UI updates.
"""
import customtkinter as ctk
from tkinter import colorchooser
from config import ThemeManager


class PropertyPanel(ctk.CTkFrame):
    """Right-side panel for editing widget or node properties."""

    def __init__(self, parent, canvas_manager, node_engine=None, node_canvas=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas_mgr = canvas_manager
        self.node_engine = node_engine
        self.node_canvas = node_canvas  # set by App
        colors = ThemeManager.colors()
        self.configure(fg_color=colors["bg_secondary"], corner_radius=0)

        self._rows: list = []  # keep references to avoid GC

        # Title
        self.title_label = ctk.CTkLabel(
            self, text="⚙️ Properties",
            font=("Segoe UI", 15, "bold"),
            text_color=colors["fg_accent"])
        self.title_label.pack(padx=10, pady=(12, 4), anchor="w")

        sep = ctk.CTkFrame(self, height=1, fg_color=colors["border"])
        sep.pack(fill="x", padx=10, pady=(0, 6))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self.no_selection_lbl = ctk.CTkLabel(
            self.scroll, text="No selection",
            text_color="#808080",
            font=("Segoe UI", 12))
        self.no_selection_lbl.pack(pady=30)

        # Register callback
        canvas_manager.set_selection_callback(self._on_selection_changed)
        canvas_manager.set_show_variables_callback(self._on_show_variables)

    def _on_selection_changed(self, var_name: str | None) -> None:
        """Handle widget selection from canvas."""
        self._clear()
        colors = ThemeManager.colors()
        if not var_name:
            # Show Project Settings
            self._add_header("🛠️ Ajustes del Proyecto", colors)
            
            view = self.canvas_mgr.views.get(self.canvas_mgr.current_view)
            if view:
                bg = view.bg_color or self.canvas_mgr.global_bg_color
                self._add_color_row_view("Color de Ventana", bg, colors)
            
            # Project Geometry
            self._add_entry_row_geom("Tamaño Ventana", self.canvas_mgr.project_geometry, colors)
            
            # Variables Button (replaces right-click menu dependencies)
            var_btn = ctk.CTkButton(self.scroll, text="🔧 Manage Variables...", height=32,
                                    fg_color=colors["header"] if "header" in colors else colors["bg_panel"],
                                    command=lambda: self.canvas_mgr._on_show_variables_requested() if self.canvas_mgr._on_show_variables_requested else None)
            var_btn.pack(fill="x", padx=8, pady=(20, 8))
            self._rows.append(var_btn)
            return

        view = self.canvas_mgr.views.get(self.canvas_mgr.current_view)
        if not view or var_name not in view.widgets: return

        wdata = view.widgets[var_name]
        colors = ThemeManager.colors()

        self._add_name_row("Variable Name", var_name, colors)
        self._add_label("Type", wdata["type"], colors)

        self._add_header("📍 Position", colors)
        self._add_slider_row("X", wdata["rx"], 0.0, 1.0, lambda v: self._update_pos(var_name, "rx", v), colors)
        self._add_slider_row("Y", wdata["ry"], 0.0, 1.0, lambda v: self._update_pos(var_name, "ry", v), colors)
        self._add_slider_row("Width", wdata["rw"], 0.02, 1.0, lambda v: self._update_size(var_name, "rw", v), colors)
        self._add_slider_row("Height", wdata["rh"], 0.02, 1.0, lambda v: self._update_size(var_name, "rh", v), colors)

        self._add_header("🎨 Properties", colors)
        props = wdata["props"]
        for key, val in props.items():
            if key == "variable_key":
                self._add_variable_key_row(key, val, var_name, colors)
            elif "color" in key.lower(): self._add_color_row(key, val, var_name, colors)
            elif isinstance(val, (int, float)) and key not in ("from_", "to"):
                self._add_slider_row(key, val, 0, 100, lambda v, k=key: self._update_prop(var_name, k, v), colors)
            elif isinstance(val, str): self._add_entry_row(key, val, var_name, colors)
            elif isinstance(val, list): self._add_entry_row(key, ", ".join(str(v) for v in val), var_name, colors, is_list=True)

        del_btn = ctk.CTkButton(self.scroll, text="🗑️ Delete Widget", fg_color=colors["error"], command=lambda: self._delete_widget(var_name))
        del_btn.pack(fill="x", padx=8, pady=(16, 8))
        self._rows.append(del_btn)

    def _add_entry_row_geom(self, key: str, value: str, colors: dict) -> None:
        row = ctk.CTkFrame(self.scroll, fg_color="transparent"); row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(row, text=key, width=80, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        entry = ctk.CTkEntry(row, height=26, font=("Segoe UI", 11), fg_color=colors["bg_primary"], border_color=colors["border"])
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0)); entry.insert(0, value)
        
        def _update(event=None):
            self.canvas_mgr.project_geometry = entry.get()
            self.canvas_mgr._trigger_change()
            
        entry.bind("<FocusOut>", _update)
        entry.bind("<Return>", _update)
        entry.bind("<KeyRelease>", _update)
        self._rows.append(row)

    def _on_node_selection_changed(self, node_id: str | None) -> None:
        """Handle node selection from NodeCanvas."""
        self._clear()
        if not node_id or not self.node_engine: return
        node = self.node_engine.nodes.get(node_id)
        if not node: return
        colors = ThemeManager.colors()

        self._add_header(f"🔗 {node.title}", colors)
        self._add_label("ID", node.id, colors)

        if node.node_type == "event":
            self._add_option_row("Trigger", node.params.get("trigger", "Click"), ["Click", "Hover"], 
                                lambda v: self._update_node_param(node_id, "trigger", v), colors)
            self._add_option_row("Widget", node.var_name, self._get_all_widget_names(), 
                                lambda v: self._update_node_param_top(node_id, "var_name", v), colors)

        elif node.node_type == "action":
            tasks = node.params.get("tasks", [])
            for i, task in enumerate(tasks):
                self._add_header(f"⚡ Task {i+1}", colors)
                actions = ["change_text", "change_color", "change_view", "save_variable", "print_variable"]
                current_action = task.get("action", "")
                
                # We need a dynamic update callback for dicts inside the tasks list
                def _update_task(idx, param, val, refresh=False):
                    self.node_engine.nodes[node_id].params["tasks"][idx][param] = val
                    if self.node_canvas: self.node_canvas.redraw_all()
                    self.canvas_mgr._trigger_change()
                    if refresh: self.after(10, lambda: self._on_node_selection_changed(node_id))
                    
                self._add_option_row("Action", current_action, actions, 
                                    lambda v, idx=i: _update_task(idx, "action", v, True), colors)
                
                if current_action != "save_variable":
                    self._add_option_row("Target", task.get("target", ""), self._get_all_widget_names(), 
                                        lambda v, idx=i: _update_task(idx, "target", v), colors)
                                    
                if current_action == "change_text":
                    self._add_entry_row_dict("Text", task.get("value", ""), lambda v, idx=i: _update_task(idx, "value", v), colors)
                elif current_action == "change_color":
                    self._add_color_row_dict("Text Color", task.get("text_color", ""), lambda v, idx=i: _update_task(idx, "text_color", v, True), colors)
                    self._add_color_row_dict("Background", task.get("fg_color", ""), lambda v, idx=i: _update_task(idx, "fg_color", v, True), colors)
                elif current_action == "change_view":
                    views = list(self.canvas_mgr.views.keys())
                    self._add_option_row("View", task.get("view_name", ""), views,
                                        lambda v, idx=i: _update_task(idx, "view_name", v), colors)
                elif current_action == "save_variable":
                    entries = self._get_widgets_by_type("CTkEntry")
                    current_src = task.get("source_entry", "")
                    current_var = task.get("target_var", "")
                    if not current_src and entries and entries[0] != "None Setup":
                        current_src = entries[0]
                        self.node_engine.nodes[node_id].params["tasks"][i]["source_entry"] = current_src
                    if not current_var:
                        current_var = "my_var"
                        self.node_engine.nodes[node_id].params["tasks"][i]["target_var"] = current_var
                    self._add_option_row("Source Entry", current_src, entries,
                                        lambda v, idx=i: _update_task(idx, "source_entry", v), colors)
                    self._add_entry_row_dict("Variable Name", current_var, lambda v, idx=i: _update_task(idx, "target_var", v), colors)
                elif current_action == "print_variable":
                    self._add_entry_row_dict("Format String", task.get("format_string", "Hola {my_var}"), lambda v, idx=i: _update_task(idx, "format_string", v), colors)
                
                # Delete task button if more than 1
                if len(tasks) > 1:
                    del_btn = ctk.CTkButton(self.scroll, text="✖ Remove Task", fg_color="transparent", text_color=colors["error"], hover_color=colors["bg_primary"],
                                            height=24, command=lambda idx=i: self._remove_action_task(node_id, idx))
                    del_btn.pack(fill="x", padx=8, pady=(2, 6))
                    self._rows.append(del_btn)
            
            # Add Task Button
            add_btn = ctk.CTkButton(self.scroll, text="➕ Add Task", fg_color=colors.get("header", colors.get("bg_panel", "#333333")), hover_color=colors.get("fg_accent", "#50e3c2"),
                                    command=lambda: self._add_action_task(node_id))
            add_btn.pack(fill="x", padx=8, pady=(10, 10))
            self._rows.append(add_btn)

        elif node.node_type == "decision":
            entries = self._get_widgets_by_type("CTkEntry") + self._get_widgets_by_type("CTkEntryNum")
            vars_list = list(self.canvas_mgr.project_variables.keys()) if hasattr(self.canvas_mgr, 'project_variables') else []
            left_opts = entries + vars_list
            if not left_opts or left_opts == ["None Setup"]:
                left_opts = [""]
                
            conds = node.params.get("conditions", [])
            for i, cond in enumerate(conds):
                header_text = "❓ Condición SÍ" if len(conds) == 1 else f"❓ Condición {i+1} (C{i})"
                self._add_header(header_text, colors)
                
                def _update_cond(idx, param, val):
                    self.node_engine.nodes[node_id].params["conditions"][idx][param] = val
                    if self.node_canvas: self.node_canvas.redraw_all()
                    self.canvas_mgr._trigger_change()

                current_left = cond.get("left_var", "")
                if not current_left and left_opts and left_opts[0] != "":
                    current_left = left_opts[0]
                    self.node_engine.nodes[node_id].params["conditions"][i]["left_var"] = current_left
                        
                self._add_option_row("Left Var", current_left, left_opts,
                                    lambda v, idx=i: _update_cond(idx, "left_var", v), colors)
                                    
                ops = node.params.get("operators_available", ["==", "!=", ">", "<", ">=", "<="])
                self._add_option_row("Operator", cond.get("operator", "=="), ops,
                                    lambda v, idx=i: _update_cond(idx, "operator", v), colors)
                                    
                self._add_entry_row_dict("Right Var/Literal", cond.get("right_var", ""), lambda v, idx=i: _update_cond(idx, "right_var", v), colors)
                
                if len(conds) > 1:
                    del_btn = ctk.CTkButton(self.scroll, text="✖ Remove Cond", fg_color="transparent", text_color=colors["error"], hover_color=colors["bg_primary"],
                                            height=24, command=lambda idx=i: self._remove_decision_cond(node_id, idx))
                    del_btn.pack(fill="x", padx=8, pady=(2, 6))
                    self._rows.append(del_btn)
                    
            # Add Condition Button
            add_btn = ctk.CTkButton(self.scroll, text="➕ Add Condition (ELIF)", fg_color=colors.get("header", colors.get("bg_panel", "#333333")), hover_color=colors.get("fg_accent", "#50e3c2"),
                                    command=lambda: self._add_decision_cond(node_id))
            add_btn.pack(fill="x", padx=8, pady=(10, 10))
            self._rows.append(add_btn)

        # MANUAL CONNECTION
        if node.node_type != "decision":
            self._add_header("➡️ Next Step", colors)
            other_nodes = self._get_other_nodes(node_id)
            current_conns = self.node_engine.get_connections_for_node(node_id)
            linked_to = "None"
            for c in current_conns:
                if c.from_node == node_id:
                    tn = self.node_engine.nodes.get(c.to_node)
                    if tn: linked_to = f"{tn.title} ({tn.id[:4]})"
            
            self._add_option_row("Enlazar a", linked_to, ["None"] + [n["label"] for n in other_nodes], 
                                lambda v: self._manual_connect(node_id, v, other_nodes), colors)
        else:
            other_nodes = self._get_other_nodes(node_id)
            current_conns = self.node_engine.get_connections_for_node(node_id)
            conds_len = len(node.params.get("conditions", []))
            
            for i in range(conds_len):
                header = "➡️ SÍ (Verdadero)" if conds_len == 1 else f"➡️ SÍ (C{i})"
                self._add_header(header, colors)
                port_name = f"cond_{i}"
                linked = "None"
                for c in current_conns:
                    if c.from_node == node_id and c.from_port == port_name:
                        tn = self.node_engine.nodes.get(c.to_node)
                        if tn: linked = f"{tn.title} ({tn.id[:4]})"
                
                row_label = "Enlazar si CUMPLE" if conds_len == 1 else f"Enlazar si {i}"
                self._add_option_row(row_label, linked, ["None"] + [n["label"] for n in other_nodes], 
                                    lambda v, p=port_name: self._manual_connect(node_id, v, other_nodes, p), colors)

            header_else = "➡️ SINO (Falso)" if conds_len == 1 else "➡️ SINO / Otros"
            self._add_header(header_else, colors)
            linked_else = "None"
            for c in current_conns:
                if c.from_node == node_id and c.from_port == "else":
                    tn = self.node_engine.nodes.get(c.to_node)
                    if tn: linked_else = f"{tn.title} ({tn.id[:4]})"
            
            row_label_else = "Enlazar si NO CUMPLE" if conds_len == 1 else "Enlazar Rama SINO"
            self._add_option_row(row_label_else, linked_else, ["None"] + [n["label"] for n in other_nodes], 
                                lambda v: self._manual_connect(node_id, v, other_nodes, "else"), colors)

        # Delete Node
        del_btn = ctk.CTkButton(self.scroll, text="🗑️ Delete Node", fg_color=colors["error"], 
                               command=lambda: self._delete_node(node_id))
        del_btn.pack(fill="x", padx=8, pady=(16, 8))
        self._rows.append(del_btn)

    def _add_action_task(self, node_id):
        if self.node_engine and node_id in self.node_engine.nodes:
            self.node_engine.nodes[node_id].params.setdefault("tasks", []).append({"action": "change_text", "target": "", "value": ""})
            self._on_node_selection_changed(node_id)
            self.canvas_mgr._trigger_change()
            
    def _remove_action_task(self, node_id, idx):
        if self.node_engine and node_id in self.node_engine.nodes:
            self.node_engine.nodes[node_id].params.get("tasks", []).pop(idx)
            self._on_node_selection_changed(node_id)
            self.canvas_mgr._trigger_change()
            
    def _add_decision_cond(self, node_id):
        if self.node_engine and node_id in self.node_engine.nodes:
            self.node_engine.nodes[node_id].params.setdefault("conditions", []).append({"left_var": "", "operator": "==", "right_var": ""})
            self.node_engine.update_decision_ports(node_id)
            self._on_node_selection_changed(node_id)
            if self.node_canvas: self.node_canvas.redraw_all()
            self.canvas_mgr._trigger_change()
            
    def _remove_decision_cond(self, node_id, idx):
        if self.node_engine and node_id in self.node_engine.nodes:
            self.node_engine.nodes[node_id].params.get("conditions", []).pop(idx)
            self.node_engine.update_decision_ports(node_id)
            self._on_node_selection_changed(node_id)
            if self.node_canvas: self.node_canvas.redraw_all()
            self.canvas_mgr._trigger_change()

    def _manual_connect(self, source_id: str, target_label: str, other_nodes: list, port: str = None) -> None:
        if not self.node_engine: return
        src_n = self.node_engine.nodes.get(source_id)
        if not src_n: return
        
        source_port = port if port else (src_n.outputs[0] if src_n.outputs else "trigger")
        self.node_engine.connections = [c for c in self.node_engine.connections if not (c.from_node == source_id and c.from_port == source_port)]
        
        if target_label != "None":
            target_id = next((n["id"] for n in other_nodes if n["label"] == target_label), None)
            if target_id:
                tgt_n = self.node_engine.nodes.get(target_id)
                if tgt_n:
                    self.node_engine.connect(source_id, source_port,
                                             target_id, tgt_n.inputs[0] if tgt_n.inputs else "trigger")
        if self.node_canvas:
            self.node_canvas.auto_layout()
            self.node_canvas.redraw_all()
        self.canvas_mgr._trigger_change()

    def _get_other_nodes(self, current_id: str) -> list:
        others = []
        if self.node_engine:
            for nid, n in self.node_engine.nodes.items():
                if nid != current_id: others.append({"id": nid, "label": f"{n.title} ({nid[:4]})"})
        return others

    def _on_show_variables(self) -> None:
        self._clear()
        colors = ThemeManager.colors()
        self._add_header("🔧 Variables del Proyecto", colors)
        
        # Row 1: Clave & Valor
        add_frame_cv = ctk.CTkFrame(self.scroll, fg_color="transparent")
        add_frame_cv.pack(fill="x", padx=8, pady=2)
        k_entry = ctk.CTkEntry(add_frame_cv, width=60, placeholder_text="Clave", font=("Segoe UI", 11), fg_color=colors["bg_primary"], border_color=colors["border"])
        k_entry.pack(side="left", padx=2, fill="x", expand=True)
        v_entry = ctk.CTkEntry(add_frame_cv, width=60, placeholder_text="Valor", font=("Segoe UI", 11), fg_color=colors["bg_primary"], border_color=colors["border"])
        v_entry.pack(side="left", padx=2, fill="x", expand=True)
        
        # Row 2: Tipo & Botón Guardar
        add_frame_tb = ctk.CTkFrame(self.scroll, fg_color="transparent")
        add_frame_tb.pack(fill="x", padx=8, pady=(2, 12))
        
        type_var = ctk.StringVar(value="Texto")
        type_menu = ctk.CTkOptionMenu(add_frame_tb, values=["Texto", "Número", "Bool"], variable=type_var, width=80, font=("Segoe UI", 11), fg_color=colors["bg_primary"])
        type_menu.pack(side="left", padx=2)
        
        def _add_var():
            k = k_entry.get().strip()
            v_str = v_entry.get().strip()
            t = type_var.get()
            if k and v_str:
                if t == "Número":
                    try: v = float(v_str) if "." in v_str else int(v_str)
                    except ValueError: v = 0
                elif t == "Bool":
                    v = v_str.lower() == "true"
                else:
                    v = v_str
                    
                self.canvas_mgr.project_variables[k] = v
                self._on_show_variables()
                self.canvas_mgr._trigger_change()
                
        add_btn = ctk.CTkButton(add_frame_tb, text="Guardar Variable", height=28, fg_color=colors.get("success", "#28a745"), hover_color="#218838", command=_add_var)
        add_btn.pack(side="left", fill="x", expand=True, padx=(4, 2))
        
        self._rows.extend([add_frame_cv, add_frame_tb])
        
        sep = ctk.CTkFrame(self.scroll, height=1, fg_color=colors["border"])
        sep.pack(fill="x", padx=10, pady=6)
        
        for key, val in dict(self.canvas_mgr.project_variables).items():
            row = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=key, width=70, anchor="w", font=("Segoe UI", 11), text_color=colors["fg_accent"]).pack(side="left")
            entry = ctk.CTkEntry(row, height=26, font=("Segoe UI", 11), fg_color=colors["bg_primary"], border_color=colors["border"])
            entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
            entry.insert(0, str(val))
            
            def _make_update(k, ent):
                def _update(e=None):
                    self.canvas_mgr.project_variables[k] = ent.get()
                    self.canvas_mgr._trigger_change()
                return _update
                
            entry.bind("<FocusOut>", _make_update(key, entry))
            entry.bind("<Return>", _make_update(key, entry))
            entry.bind("<KeyRelease>", _make_update(key, entry))
            
            def _make_del(k):
                def _del():
                    del self.canvas_mgr.project_variables[k]
                    self._on_show_variables()
                    self.canvas_mgr._trigger_change()
                return _del
                
            del_btn = ctk.CTkButton(row, text="❌", width=30, fg_color="transparent", hover_color=colors["error"], text_color=colors["error"], command=_make_del(key))
            del_btn.pack(side="left")
            self._rows.append(row)

    # ─── Entry Updates ──────────────────────────────────────────
    def _add_entry_row_node(self, key: str, value: str, node_id: str, param_key: str, colors: dict) -> None:
        row = ctk.CTkFrame(self.scroll, fg_color="transparent"); row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(row, text=key, width=70, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        entry = ctk.CTkEntry(row, height=26, font=("Segoe UI", 11), fg_color=colors["bg_primary"], border_color=colors["border"])
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0)); entry.insert(0, value)
        
        entry.bind("<FocusOut>", lambda e: self._update_node_param(node_id, param_key, entry.get()))
        entry.bind("<Return>", lambda e: self._update_node_param(node_id, param_key, entry.get()))
        self._rows.append(row)

    def _add_entry_row_dict(self, label, current_val, update_cb, cols):
        """Entry field that calls update_cb(value) on FocusOut/Return."""
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r, text=label, width=90, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        entry = ctk.CTkEntry(r, height=26, font=("Segoe UI", 11), fg_color=cols["bg_primary"], border_color=cols["border"])
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        entry.insert(0, current_val or "")
        def _save(e=None): update_cb(entry.get())
        entry.bind("<FocusOut>", _save)
        entry.bind("<Return>", _save)
        self._rows.append(r)

    def _add_color_row_dict(self, label, current_val, update_cb, cols):
        """Color-pick button that calls update_cb(hex_color)."""
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r, text=label, width=90, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        display = current_val if current_val else cols["bg_primary"]
        btn_text = current_val if current_val else "Pick"
        btn = ctk.CTkButton(r, text=btn_text, width=70, height=24, fg_color=display,
                            command=lambda: self._trigger_dict_color_pick(label, update_cb))
        btn.pack(side="left", padx=4)
        self._rows.append(r)

    def _trigger_dict_color_pick(self, label, update_cb):
        color = colorchooser.askcolor(title=f"Pick {label}")[1]
        if color: update_cb(color)

    def _update_node_param(self, nid, k, v, refresh_panel=False):
        if self.node_engine and nid in self.node_engine.nodes:
            if self.node_engine.nodes[nid].params.get(k) == v:
                return # Prevent infinite recursion
            self.node_engine.nodes[nid].params[k] = v
            if self.node_canvas: self.node_canvas.redraw_all()
            self.canvas_mgr._trigger_change()
            if refresh_panel:
                self.after(10, lambda: self._on_node_selection_changed(nid))

    def _update_node_param_top(self, nid, k, v):
        if self.node_engine and nid in self.node_engine.nodes:
            if getattr(self.node_engine.nodes[nid], k, None) == v:
                return
            setattr(self.node_engine.nodes[nid], k, v)
            if self.node_canvas: self.node_canvas.redraw_all()
            self.canvas_mgr._trigger_change()

    # ─── Layout helpers ───────────────────────────────────────────
    def _clear(self):
        for child in list(self.scroll.winfo_children()):
            try:
                child.pack_forget()
                self.after(50, child.destroy)
            except Exception:
                pass
        self._rows.clear()

    def _add_header(self, text, cols):
        l = ctk.CTkLabel(self.scroll, text=text, font=("Segoe UI", 13, "bold"), text_color=cols["fg_accent"], anchor="w")
        l.pack(fill="x", padx=8, pady=(10, 2)); self._rows.append(l)

    def _add_label(self, k, v, cols):
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=1)
        ctk.CTkLabel(r, text=k, width=70, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        ctk.CTkLabel(r, text=v, anchor="w", font=("Segoe UI", 11), text_color=cols["fg_text"]).pack(side="left", fill="x")
        self._rows.append(r)

    def _add_entry_row(self, key, value, var_name, colors, is_list=False):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent"); row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(row, text=key, width=70, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        entry = ctk.CTkEntry(row, height=26, font=("Segoe UI", 11), fg_color=colors["bg_primary"], border_color=colors["border"])
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0)); entry.insert(0, value)
        entry.bind("<FocusOut>", lambda e: self.canvas_mgr.update_widget_props(var_name, {key: (entry.get().split(",") if is_list else entry.get())}))
        entry.bind("<Return>", lambda e: self.canvas_mgr.update_widget_props(var_name, {key: (entry.get().split(",") if is_list else entry.get())}))
        entry.bind("<KeyRelease>", lambda e: self.canvas_mgr.update_widget_props(var_name, {key: (entry.get().split(",") if is_list else entry.get())}))
        self._rows.append(row)

    def _add_variable_key_row(self, key, value, var_name, colors):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent"); row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(row, text="Var Key", width=70, anchor="w", font=("Segoe UI", 11, "bold"), text_color=colors["fg_accent"]).pack(side="left")
        entry = ctk.CTkEntry(row, height=26, font=("Segoe UI", 11), fg_color=colors["bg_primary"], border_color=colors["border"])
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0)); entry.insert(0, value)
        
        # Tracks the last committed key so we can remove it if the user renames.
        _prev_key = [value]  # mutable cell

        def _update_varkey(e=None):
            val = entry.get().strip()
            if val and not val.isidentifier():
                entry.configure(border_color=colors["error"])
                return
            entry.configure(border_color=colors["border"])
            old = _prev_key[0]
            # Remove the old key from project_variables if it changed
            if old and old != val and old in self.canvas_mgr.project_variables:
                del self.canvas_mgr.project_variables[old]
            if val and val not in self.canvas_mgr.project_variables:
                self.canvas_mgr.project_variables[val] = ""
            _prev_key[0] = val
            self.canvas_mgr.update_widget_props(var_name, {key: val})

        # Only commit on FocusOut / Enter — NOT on every KeyRelease
        entry.bind("<FocusOut>", _update_varkey)
        entry.bind("<Return>", _update_varkey)
        self._rows.append(row)

    def _add_entry_row_node(self, label, current_val, node_id, param_key, cols):
        """Render a text field that saves to a node's param dict on edit."""
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r, text=label, width=90, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        entry = ctk.CTkEntry(r, height=26, font=("Segoe UI", 11), fg_color=cols["bg_primary"], border_color=cols["border"])
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        entry.insert(0, current_val or "")
        def _save(e=None):
            val = entry.get()
            if self.node_engine and node_id in self.node_engine.nodes:
                self.node_engine.nodes[node_id].params[param_key] = val
                self.canvas_mgr._trigger_change()
        entry.bind("<FocusOut>", _save)
        entry.bind("<Return>", _save)
        entry.bind("<KeyRelease>", _save)
        self._rows.append(r)

    def _add_option_row(self, k, c, v, cb, cols):
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r, text=k, width=70, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        var = ctk.StringVar(value=c if c else (v[0] if v else "?"))
        m = ctk.CTkOptionMenu(r, values=v, variable=var, height=26, font=("Segoe UI", 11), fg_color=cols["bg_primary"], command=cb)
        m.pack(side="left", fill="x", expand=True, padx=(4, 0)); self._rows.append(r)

    def _add_name_row(self, k, v, cols):
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r, text=k, width=70, anchor="w", font=("Segoe UI", 11), text_color=cols["fg_accent"]).pack(side="left")
        entry = ctk.CTkEntry(r, height=26, font=("Segoe UI", 11, "bold"), fg_color=cols["bg_primary"], border_color=cols["fg_accent"])
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0)); entry.insert(0, v)
        entry.bind("<FocusOut>", lambda e: self._on_selection_changed(self.canvas_mgr.rename_widget(v, entry.get())))
        entry.bind("<Return>", lambda e: self._on_selection_changed(self.canvas_mgr.rename_widget(v, entry.get())))
        self._rows.append(r)

    def _add_slider_row(self, k, v, min_v, max_v, cb, cols):
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(r, text=k, width=60, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        
        is_geom = (min_v == 0.0 and max_v == 1.0)
        display_val = float(v) * 10.0 if is_geom else float(v)
        
        entry_var = ctk.StringVar(value=f"{display_val:.1f}")
        entry = ctk.CTkEntry(r, width=35, height=22, font=("Segoe UI", 10), textvariable=entry_var)
        entry.pack(side="right", padx=(4, 0))

        def _on_slide(val):
            disp = val * 10.0 if is_geom else val
            entry_var.set(f"{disp:.1f}")
            cb(val)

        def _on_entry(event=None):
            try:
                val = float(entry_var.get())
                real_val = val / 10.0 if is_geom else val
                real_val = max(min_v, min(max_v, real_val))
                slider.set(real_val)
                cb(real_val)
            except ValueError:
                pass

        entry.bind("<Return>", _on_entry)
        entry.bind("<FocusOut>", _on_entry)

        slider = ctk.CTkSlider(r, from_=min_v, to=max_v, command=_on_slide, height=14)
        slider.set(float(v))
        slider.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self._rows.append(r)

    def _add_color_row(self, k, v, vn, cols):
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r, text=k, width=70, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        btn = ctk.CTkButton(r, text="Pick", width=50, height=24, command=lambda: self._pick_color(vn, k))
        btn.pack(side="left", padx=4); self._rows.append(r)

    def _update_pos(self, vn, a, val):
        view = self.canvas_mgr.views.get(self.canvas_mgr.current_view)
        if view and vn in view.widgets: view.widgets[vn][a] = val; self.canvas_mgr._render_view()

    def _update_size(self, vn, d, val):
        view = self.canvas_mgr.views.get(self.canvas_mgr.current_view)
        if view and vn in view.widgets: view.widgets[vn][d] = val; self.canvas_mgr._render_view()

    def _update_prop(self, vn, k, v): self.canvas_mgr.update_widget_props(vn, {k: v})

    def _update_view_bg(self, color):
        view = self.canvas_mgr.views.get(self.canvas_mgr.current_view)
        if view and color:
            view.bg_color = color
            self.canvas_mgr._render_view()
            self.canvas_mgr._trigger_change()

    def _pick_color(self, vn, k):
        color = colorchooser.askcolor(title=f"Pick {k}")[1]
        if color: self.canvas_mgr.update_widget_props(vn, {k: color})
        
    def _add_color_row_view(self, k, v, cols):
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r, text=k, width=120, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        btn = ctk.CTkButton(r, text="Pick Color" if not v else v, width=80, height=24, 
                            fg_color=v if v else cols["bg_primary"],
                            command=lambda: self._trigger_view_color_pick())
        btn.pack(side="left", padx=4); self._rows.append(r)
        
    def _trigger_view_color_pick(self):
        color = colorchooser.askcolor(title="Background Color")[1]
        if color:
            self._update_view_bg(color)
            self._on_selection_changed(None) # Refresh settings UI
            
    def _add_color_row_node(self, k, v, nid, param_key, cols):
        r = ctk.CTkFrame(self.scroll, fg_color="transparent"); r.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(r, text=k, width=70, anchor="w", font=("Segoe UI", 11), text_color="#999999").pack(side="left")
        btn = ctk.CTkButton(r, text="Pick" if not v else v, width=60, height=24, 
                            fg_color=v if v else cols["bg_primary"],
                            command=lambda: self._trigger_node_color_pick(nid, param_key))
        btn.pack(side="left", padx=4); self._rows.append(r)
        
    def _trigger_node_color_pick(self, nid, param_key):
        color = colorchooser.askcolor(title=f"Pick {param_key}")[1]
        if color:
            self._update_node_param(nid, param_key, color, refresh_panel=True)

    def _get_all_widget_names(self): return sorted(list(set(n for v in self.canvas_mgr.views.values() for n in v.widgets.keys()))) or ["?"]

    def _get_widgets_by_type(self, wtype: str):
        res = sorted(list(set(n for v in self.canvas_mgr.views.values() for n, w in v.widgets.items() if w.get("type") == wtype)))
        return res if res else ["None Setup"]

    def _delete_widget(self, vn): self.canvas_mgr.delete_widget(vn); self._on_selection_changed(None)

    def _delete_node(self, nid):
        if self.node_engine: self.node_engine.delete_node(nid); self._on_node_selection_changed(None); self.canvas_mgr._trigger_change()
        if self.node_canvas: 
            self.node_canvas.auto_layout()
            self.node_canvas.redraw_all()
