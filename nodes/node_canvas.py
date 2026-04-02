"""
node_canvas.py — Visual node editor using tkinter.Canvas.
Fixed: Connection logic with drag-to-connect and click-click fallback.
Fixed: Selection persistence by blocking click propagation to background.
"""
import tkinter as tk
import customtkinter as ctk
from nodes.node_engine import NodeEngine, Node, Connection
from nodes.node_types import NODE_COLORS, NODE_FACTORIES
from config import ThemeManager


NODE_W = 180
NODE_H = 80
PORT_R = 7
HEADER_H = 28


class NodeCanvas(ctk.CTkFrame):
    """Visual node editor where users create logic flows."""

    def __init__(self, parent, node_engine: NodeEngine,
                 canvas_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.engine = node_engine
        self.canvas_mgr = canvas_manager
        colors = ThemeManager.colors()
        self.configure(fg_color=colors["bg_primary"], corner_radius=0)

        # Interaction state
        self._drag_node: str | None = None
        self._drag_offset = (0, 0)
        self._connecting_from: tuple | None = None  # (node_id, port_name)
        self._temp_line: int | None = None
        self._selected_node: str | None = None
        self._on_node_selected = None
        self._node_counter = 0
        self._last_click_item = False

        # Toolbar
        toolbar = ctk.CTkFrame(self, height=36, fg_color=colors["bg_secondary"],
                               corner_radius=0)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        ctk.CTkLabel(toolbar, text="🔗 Node Editor",
                     font=("Segoe UI", 13, "bold"),
                     text_color=colors["fg_accent"]).pack(side="left", padx=10)

        for ntype, (label, _) in NODE_FACTORIES.items():
            ncolors = NODE_COLORS[ntype]
            btn = ctk.CTkButton(
                toolbar, text=label, height=26, width=90,
                font=("Segoe UI", 11),
                fg_color=ncolors["bg"],
                hover_color=ncolors["header"],
                text_color=ncolors["text"],
                corner_radius=4,
                command=lambda t=ntype: self._add_node(t))
            btn.pack(side="left", padx=3, pady=5)

        ctk.CTkButton(toolbar, text="🗑️ Clear All", height=26, width=80,
                      font=("Segoe UI", 11),
                      fg_color=colors["error"],
                      corner_radius=4,
                      command=self._clear_all).pack(side="right", padx=8, pady=5)

        # Canvas area with scrollbars
        canvas_container = ctk.CTkFrame(self, fg_color="transparent")
        canvas_container.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(canvas_container, bg=colors["bg_primary"],
                                highlightthickness=0, bd=0)
        
        hbar = ctk.CTkScrollbar(canvas_container, orientation="horizontal", command=self.canvas.xview)
        hbar.pack(side="bottom", fill="x")
        vbar = ctk.CTkScrollbar(canvas_container, orientation="vertical", command=self.canvas.yview)
        vbar.pack(side="right", fill="y")
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        # Global Bindings
        self.canvas.bind("<Button-1>", self._on_bg_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<B1-Motion>", self._on_motion) # For drag connection
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def set_on_node_selected(self, callback) -> None:
        self._on_node_selected = callback

    # ─── Add Nodes ────────────────────────────────────────────────
    def _add_node(self, node_type: str) -> None:
        label, factory = NODE_FACTORIES[node_type]
        self._node_counter += 1
        
        # Calculate roughly center but offset for new nodes within the view
        scroll_x = int(self.canvas.canvasx(0))
        scroll_y = int(self.canvas.canvasy(0))
        x = round((scroll_x + 60 + (self._node_counter % 3) * 200) / 20) * 20
        y = round((scroll_y + 60 + (self._node_counter // 3) * 120) / 20) * 20

        var_name = ""
        if self.canvas_mgr and self.canvas_mgr.current_view:
            view = self.canvas_mgr.views.get(self.canvas_mgr.current_view)
            if view and view.widgets:
                var_name = list(view.widgets.keys())[0]

        params = factory(var_name=var_name) if node_type == "event" else factory()
        if node_type in ("action", "validate") and var_name:
            params["target"] = var_name

        node = self.engine.add_node(node_type, label, var_name, params, x, y)
        self.auto_layout()
        self._draw_node(node)
        self._on_node_click(node.id, None)
        if self.canvas_mgr: self.canvas_mgr._trigger_change()

    def _clear_all(self) -> None:
        if self.engine:
            self.engine.clear()
            self._selected_node = None
            self._connecting_from = None
            self.redraw_all()
            if self.canvas_mgr: self.canvas_mgr._trigger_change()

    def redraw_all(self) -> None:
        self.canvas.delete("all")
        for node in self.engine.nodes.values():
            self._draw_node(node)
        for conn in self.engine.connections:
            self._draw_connection(conn)
        
        # Update scroll region
        bbox = self.canvas.bbox("all")
        if bbox:
            min_x, min_y, max_x, max_y = bbox
            self.canvas.config(scrollregion=(min(0, min_x), min(0, min_y), max(2500, max_x + 300), max(1500, max_y + 300)))
        else:
            self.canvas.config(scrollregion=(0, 0, 2500, 1500))

    def auto_layout(self) -> None:
        """Automatically arrange nodes left-to-right based on connections."""
        if not self.engine or not self.engine.nodes: return
        
        # 1. Map incoming connections
        incoming = {nid: [] for nid in self.engine.nodes}
        for c in self.engine.connections:
            if c.to_node in incoming:
                incoming[c.to_node].append(c.from_node)
                
        roots = [nid for nid, in_conns in incoming.items() if not in_conns]
        
        # 2. Assign depths (longest path)
        levels = {}
        visited = set()
        
        def assign_level(nid, depth):
            if nid in visited: return
            visited.add(nid)
            levels.setdefault(depth, []).append(nid)
            children = [c.to_node for c in self.engine.connections if c.from_node == nid]
            for child in children:
                assign_level(child, depth + 1)
                
        for r in roots: assign_level(r, 0)
        
        # Place disconnected/cycles
        unvisited = [nid for nid in self.engine.nodes if nid not in visited]
        for u in unvisited:
            levels.setdefault(0, []).append(u)
            
        # 3. Apply coordinates
        x_spacing = 280
        y_spacing = 140
        start_x, start_y = 60, 60
        
        for depth in sorted(levels.keys()):
            col_nodes = levels[depth]
            for idx, nid in enumerate(col_nodes):
                node = self.engine.nodes[nid]
                node.x = start_x + (depth * x_spacing)
                node.y = start_y + (idx * y_spacing)



    # ─── Drawing ──────────────────────────────────────────────────
    def _draw_node(self, node: Node) -> None:
        tag = f"node_{node.id}"
        colors = NODE_COLORS[node.node_type]
        
        is_selected = (node.id == self._selected_node)
        border_color = "#00ffff" if is_selected else colors["header"]
        border_width = 3 if is_selected else 1
        is_decision = node.node_type == "decision"

        if is_decision:
            pts = [
                node.x + NODE_W/2, node.y,
                node.x + NODE_W, node.y + NODE_H/2,
                node.x + NODE_W/2, node.y + NODE_H,
                node.x, node.y + NODE_H/2
            ]
            self.canvas.create_polygon(
                pts,
                fill=colors["bg"], outline=border_color, width=border_width,
                tags=(tag, "node_body")
            )
            self.canvas.create_text(
                node.x + NODE_W/2, node.y + NODE_H/2 - 10,
                text=node.title, anchor="center", fill=colors["text"],
                font=("Segoe UI", 10, "bold"), tags=(tag, "node_title"))
            
            info = f"{node.params.get('left_var', '')} {node.params.get('operator', '==')} {node.params.get('right_var', '')}"
            self.canvas.create_text(
                node.x + NODE_W/2, node.y + NODE_H/2 + 10,
                text=f"[{info[:20]}]", anchor="center", fill="#cccccc",
                font=("Consolas", 8), tags=(tag, "node_params"))
        else:
            # Body & Header
            self.canvas.create_rectangle(
                node.x, node.y, node.x + NODE_W, node.y + NODE_H,
                fill=colors["bg"], outline=border_color, width=border_width,
                tags=(tag, "node_body"))
            self.canvas.create_rectangle(
                node.x, node.y, node.x + NODE_W, node.y + HEADER_H,
                fill=colors["header"], outline=border_color, width=border_width,
                tags=(tag, "node_header"))
    
            # Text
            self.canvas.create_text(
                node.x + 10, node.y + HEADER_H // 2,
                text=node.title, anchor="w", fill=colors["text"],
                font=("Segoe UI", 10, "bold"), tags=(tag, "node_title"))
    
            info = node.var_name if node.node_type == "event" else node.params.get("action", "Action")
            self.canvas.create_text(
                node.x + 10, node.y + HEADER_H + 20,
                text=f"[{info}]", anchor="w", fill="#cccccc",
                font=("Consolas", 9), tags=(tag, "node_params"))

        # Ports
        self._draw_ports(node, tag)

        # Bindings
        for sub in ("node_body", "node_header", "node_title", "node_params"):
            items = self.canvas.find_withtag(tag)
            for item in items:
                if sub in self.canvas.gettags(item):
                    self.canvas.tag_bind(item, "<Button-1>", lambda e, nid=node.id: (self._on_node_click(nid, e), "break")[1])

    def _get_port_coords(self, node: Node, port_name: str, ptype: str) -> tuple[float, float]:
        is_decision = node.node_type == "decision"
        if is_decision:
            if ptype == "input":
                return node.x, node.y + NODE_H/2
            else:
                idx = node.outputs.index(port_name) if port_name in node.outputs else 0
                total = len(node.outputs)
                # Space them vertically between 10% and 90% of NODE_H
                spacing = 0.8 / max(1, (total - 1)) if total > 1 else 0
                y = node.y + NODE_H * (0.1 + idx * spacing if total > 1 else 0.5)
                # Add some custom offset depending if it is Else so they don't overlap too much
                return node.x + NODE_W * 0.75, y
        else:
            if ptype == "input":
                idx = node.inputs.index(port_name) if port_name in node.inputs else 0
                return node.x, node.y + HEADER_H + 30 + idx * 20
            else:
                idx = node.outputs.index(port_name) if port_name in node.outputs else 0
                return node.x + NODE_W, node.y + HEADER_H + 30 + idx * 20        

    def _draw_ports(self, node: Node, tag: str) -> None:
        # Input
        for pn in node.inputs:
            px, py = self._get_port_coords(node, pn, "input")
            p_tag = f"port_{node.id}_{pn}"
            self.canvas.create_oval(
                px - PORT_R, py - PORT_R, px + PORT_R, py + PORT_R,
                fill="#333333", outline="#ffffff", width=1,
                tags=(tag, p_tag, "port_in"))
            self.canvas.tag_bind(p_tag, "<Button-1>", lambda e, n=node.id, p=pn: (self._on_port_click(n, p, "input"), "break")[1])

        # Output
        for pn in node.outputs:
            px, py = self._get_port_coords(node, pn, "output")
            color = "#2ecc71" if pn.startswith("cond") or pn == "true" else ("#e74c3c" if pn == "else" or pn == "false" else "#ffffff")
            p_tag = f"port_{node.id}_{pn}"
            self.canvas.create_oval(
                px - PORT_R, py - PORT_R, px + PORT_R, py + PORT_R,
                fill="#333333", outline=color, width=1,
                tags=(tag, p_tag, "port_out"))
            self.canvas.tag_bind(p_tag, "<Button-1>", lambda e, n=node.id, p=pn: (self._on_port_click(n, p, "output"), "break")[1])
            if node.node_type == "decision":
                # Single condition nodes show S (Si) and N (No) for high intuition
                is_binary = len(node.outputs) == 2
                if is_binary:
                    label_text = "S" if (pn.startswith("cond") or pn == "true") else "N"
                else:
                    label_text = "E" if (pn == "else" or pn == "false") else (f"C{pn.split('_')[1]}" if pn.startswith("cond") else pn[0].upper())
                    
                self.canvas.create_text(px - 14, py, text=label_text, fill=color, font=("Segoe UI", 8, "bold"), tags=(tag, p_tag, "port_label"))

    def _draw_connection(self, conn: Connection) -> None:
        n1, n2 = self.engine.nodes.get(conn.from_node), self.engine.nodes.get(conn.to_node)
        if not n1 or not n2: return
        
        x1, y1 = self._get_port_coords(n1, conn.from_port, "output")
        x2, y2 = self._get_port_coords(n2, conn.to_port, "input")
        
        cp_offset = max(60.0, abs(x2 - x1) * 0.4)
        
        self.canvas.create_line(
            x1, y1, 
            x1 + cp_offset, y1, 
            x2 - cp_offset, y2, 
            x2, y2,
            smooth=True, fill="#50e3c2", width=3,
            arrow=tk.LAST, arrowshape=(10, 12, 4), tags="connection"
        )

    # ─── Interactions ─────────────────────────────────────────────
    def _on_node_click(self, node_id: str, event) -> None:
        self._last_click_item = True
        self._selected_node = node_id
        # Fast border update
        for nid in self.engine.nodes:
            tag = f"node_{nid}"
            col = "#00ffff" if nid == node_id else NODE_COLORS[self.engine.nodes[nid].node_type]["header"]
            w = 2 if nid == node_id else 1
            for item in self.canvas.find_withtag(tag):
                if "node_body" in self.canvas.gettags(item) or "node_header" in self.canvas.gettags(item):
                    self.canvas.itemconfig(item, outline=col, width=w)
        
        if self._on_node_selected: self._on_node_selected(node_id)

    def _on_port_click(self, node_id: str, port_name: str, ptype: str) -> None:
        self._last_click_item = True
        if self._connecting_from is None:
            if ptype == "output":
                self._connecting_from = (node_id, port_name)
        else:
            if ptype == "input":
                fn, fp = self._connecting_from
                if self.engine.connect(fn, fp, node_id, port_name):
                    self.redraw_all()
                    if self.canvas_mgr: self.canvas_mgr._trigger_change()
            self._connecting_from = None
            if self._temp_line: self.canvas.delete(self._temp_line)
            self._temp_line = None

    def _on_motion(self, event) -> None:
        if self._connecting_from:
            if self._temp_line: self.canvas.delete(self._temp_line)
            nid, pn = self._connecting_from
            n = self.engine.nodes.get(nid)
            if n:
                x1, y1 = self._get_port_coords(n, pn, "output")
                self._temp_line = self.canvas.create_line(x1, y1, event.x, event.y, fill="#999999", dash=(4,4))

    def _on_release(self, event) -> None:
        self._drag_node = None
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        # Support drop-to-connect
        if self._connecting_from:
            target = self.canvas.find_overlapping(cx, cy, cx, cy)
            for item in target:
                tags = self.canvas.gettags(item)
                if "port_in" in tags:
                    for t in tags:
                        if t.startswith("port_"):
                            _, nid, pn = t.split("_", 2)
                            self._on_port_click(nid, pn, "input")
                            return
        # If released elsewhere, but was connecting, don't necessarily cancel 
        # unless it was a background click.

    def _on_bg_click(self, event) -> None:
        if self._last_click_item:
            self._last_click_item = False
            return
        self._selected_node = None
        self._connecting_from = None
        if self._temp_line: self.canvas.delete(self._temp_line)
        self._temp_line = None
        self.redraw_all()
        if self._on_node_selected: self._on_node_selected(None)

    def _on_right_click(self, event) -> None:
        pass
