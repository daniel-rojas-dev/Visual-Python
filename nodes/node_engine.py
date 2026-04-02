"""
node_engine.py — Core node graph engine.
Manages the directed graph of nodes, connections, and execution.
Includes garbage collector for orphan nodes when widgets are deleted.
"""
import uuid
import copy


class Port:
    """Connection point on a node (input or output)."""
    __slots__ = ("name", "port_type", "node_id")

    def __init__(self, name: str, port_type: str, node_id: str):
        self.name = name
        self.port_type = port_type  # "input" or "output"
        self.node_id = node_id


class Node:
    """Base class for all node types."""

    def __init__(self, node_type: str, title: str, var_name: str = ""):
        self.id: str = uuid.uuid4().hex[:8]
        self.node_type: str = node_type   # "event", "action", "math", "script", "validate"
        self.title: str = title
        self.var_name: str = var_name      # linked widget variable name
        self.params: dict = {}             # node-specific parameters
        self.x: float = 100.0             # canvas position (absolute px for node canvas)
        self.y: float = 100.0
        self.inputs: list[str] = []       # port names
        self.outputs: list[str] = []      # port names

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "title": self.title,
            "var_name": self.var_name,
            "params": self.params,
            "x": self.x,
            "y": self.y,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }

    @staticmethod
    def from_dict(data: dict) -> "Node":
        node = Node(data["node_type"], data["title"], data.get("var_name", ""))
        node.id = data["id"]
        
        # Migration logic
        params = data.get("params", {})
        if node.node_type == "action" and "action" in params and "tasks" not in params:
            # Migrate old single-action format to tasks list
            params["tasks"] = [{"action": params.get("action", ""), "target": params.get("target", ""), "value": params.get("value", "")}]
        if node.node_type == "decision" and "left_var" in params and "conditions" not in params:
            # Migrate old single-condition to conditions list
            params["conditions"] = [{"left_var": params.get("left_var", ""), "operator": params.get("operator", "=="), "right_var": params.get("right_var", "")}]
            
        node.params = params
        node.x = data.get("x", 100)
        node.y = data.get("y", 100)
        node.inputs = data.get("inputs", [])
        
        # Migrate decision outputs if they were initialized as true/false but node has conditions
        outputs = data.get("outputs", [])
        if node.node_type == "decision":
            c_len = len(params.get("conditions", []))
            # Just rebuild ports
            outputs = [f"cond_{i}" for i in range(c_len)] + ["else"]
        node.outputs = outputs
        return node


class Connection:
    """A directed edge between two node ports."""
    __slots__ = ("id", "from_node", "from_port", "to_node", "to_port")

    def __init__(self, from_node: str, from_port: str,
                 to_node: str, to_port: str):
        self.id: str = uuid.uuid4().hex[:8]
        self.from_node = from_node
        self.from_port = from_port
        self.to_node = to_node
        self.to_port = to_port

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_node": self.from_node,
            "from_port": self.from_port,
            "to_node": self.to_node,
            "to_port": self.to_port,
        }

    @staticmethod
    def from_dict(data: dict) -> "Connection":
        conn = Connection(data["from_node"], data["from_port"],
                          data["to_node"], data["to_port"])
        conn.id = data["id"]
        return conn


class NodeEngine:
    """
    Manages the directed graph of nodes and their connections.
    Handles orphan garbage collection and execution flow.
    """

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.connections: list[Connection] = []

    # ─── Node CRUD ────────────────────────────────────────────────
    def add_node(self, node_type: str, title: str, var_name: str = "",
                 params: dict = None, x: float = 100, y: float = 100) -> Node:
        """Create and register a new node."""
        node = Node(node_type, title, var_name)
        node.params = params or {}
        node.x = x
        node.y = y

        # Define ports based on type
        if node_type == "event":
            node.outputs = ["trigger"]
        elif node_type == "action":
            node.inputs = ["trigger"]
            node.outputs = ["done"]
        elif node_type == "decision":
            node.inputs = ["trigger"]
            conds_len = len(node.params.get("conditions", [1])) if node.params else 1
            node.outputs = [f"cond_{i}" for i in range(conds_len)] + ["else"]

        self.nodes[node.id] = node
        return node

    def delete_node(self, node_id: str) -> None:
        """Delete a node and all its connections."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.connections = [
                c for c in self.connections
                if c.from_node != node_id and c.to_node != node_id
            ]

    def update_node(self, node_id: str, **kwargs) -> None:
        """Update node properties."""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            for k, v in kwargs.items():
                if hasattr(node, k):
                    setattr(node, k, v)

    def update_decision_ports(self, node_id: str) -> None:
        """Called when a decision node adds or removes conditions."""
        node = self.nodes.get(node_id)
        if not node or node.node_type != "decision": return
        c_len = len(node.params.get("conditions", []))
        new_outputs = [f"cond_{i}" for i in range(c_len)] + ["else"]
        
        # Filter connections that use ports that no longer exist
        self.connections = [c for c in self.connections if not (c.from_node == node_id and c.from_port not in new_outputs)]
        node.outputs = new_outputs

    # ─── Connections ──────────────────────────────────────────────
    def connect(self, from_node: str, from_port: str,
                to_node: str, to_port: str) -> Connection | None:
        """Create a connection between two ports."""
        if from_node not in self.nodes or to_node not in self.nodes:
            return None
        # Prevent duplicate connections
        for c in self.connections:
            if (c.from_node == from_node and c.from_port == from_port
                    and c.to_node == to_node and c.to_port == to_port):
                return None
        conn = Connection(from_node, from_port, to_node, to_port)
        self.connections.append(conn)
        return conn

    def disconnect(self, conn_id: str) -> None:
        """Remove a connection by ID."""
        self.connections = [c for c in self.connections if c.id != conn_id]

    def get_connections_for_node(self, node_id: str) -> list[Connection]:
        """Get all connections involving a node."""
        return [c for c in self.connections
                if c.from_node == node_id or c.to_node == node_id]

    # ─── Orphan Garbage Collector ─────────────────────────────────
    def gc_remove_by_var_name(self, var_name: str) -> int:
        """
        Remove all nodes linked to a deleted widget variable.
        Called by CanvasManager when a widget is deleted.
        Returns the number of nodes removed.
        """
        orphan_ids = [nid for nid, n in self.nodes.items()
                      if n.var_name == var_name]
        for nid in orphan_ids:
            self.delete_node(nid)
        return len(orphan_ids)

    def update_var_name(self, old_name: str, new_name: str) -> int:
        """
        Update all nodes linked to a renamed widget variable.
        Called when a widget is renamed.
        Returns the number of nodes updated.
        """
        count = 0
        for n in self.nodes.values():
            if n.var_name == old_name:
                n.var_name = new_name
                count += 1
            if n.params.get("target") == old_name:
                n.params["target"] = new_name
                count += 1
        return count

    # ─── Execution ────────────────────────────────────────────────
    def get_flow_from_event(self, event_node_id: str) -> list[Node]:
        """
        Traverse the graph starting from an event node.
        Returns an ordered list of nodes in execution order (BFS).
        """
        visited = set()
        flow = []
        queue = [event_node_id]
        while queue:
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            if nid in self.nodes:
                flow.append(self.nodes[nid])
            # Find outgoing connections
            for conn in self.connections:
                if conn.from_node == nid and conn.to_node not in visited:
                    queue.append(conn.to_node)
        return flow

    def get_event_nodes(self) -> list[Node]:
        """Return all event nodes (entry points)."""
        return [n for n in self.nodes.values() if n.node_type == "event"]

    # ─── Serialization ────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "connections": [c.to_dict() for c in self.connections],
        }

    def from_dict(self, data: dict) -> None:
        self.nodes.clear()
        self.connections.clear()
        for nid, ndata in data.get("nodes", {}).items():
            self.nodes[nid] = Node.from_dict(ndata)
        for cdata in data.get("connections", []):
            conn = Connection.from_dict(cdata)
            # Migrate connections from true/false to cond_0/else
            if self.nodes.get(conn.from_node) and self.nodes[conn.from_node].node_type == "decision":
                if conn.from_port == "true": conn.from_port = "cond_0"
                if conn.from_port == "false": conn.from_port = "else"
            self.connections.append(conn)

    def clear(self) -> None:
        self.nodes.clear()
        self.connections.clear()
