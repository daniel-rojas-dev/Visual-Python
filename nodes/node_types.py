"""
node_types.py — Concrete node type definitions.
Event, Action, Math, Script, and Validation nodes.
"""
from config import EVENT_TRIGGERS, ACTION_TYPES


def create_event_node_params(var_name: str = "", trigger: str = "Click") -> dict:
    """Parameters for an Event Node."""
    return {
        "var_name": var_name,
        "trigger": trigger,
        "triggers_available": EVENT_TRIGGERS,
    }


def create_action_node_params(target: str = "", action: str = "change_text",
                               value: str = "") -> dict:
    """Parameters for an Action Node."""
    return {
        "target": target,
        "action": action,
        "value": value,
        "actions_available": ACTION_TYPES,
    }


def create_decision_node_params(left_var: str = "", operator: str = "==",
                                right_var: str = "") -> dict:
    """Parameters for a Decision (If/Else) Node."""
    return {
        "left_var": left_var,
        "operator": operator,
        "right_var": right_var,
        "operators_available": ["==", "!=", ">", "<", ">=", "<="]
    }




# ─── Node color mapping (for node_canvas rendering) ────────────
NODE_COLORS = {
    "event":    {"bg": "#e74c3c", "header": "#c0392b", "text": "#ffffff"},
    "action":   {"bg": "#2ecc71", "header": "#27ae60", "text": "#ffffff"},
    "decision": {"bg": "#9b59b6", "header": "#8e44ad", "text": "#ffffff"},
}

# ─── Node factory shortcut ────────────────────────────────────
NODE_FACTORIES = {
    "event":    ("🎯 Event",    create_event_node_params),
    "action":   ("⚡ Action",   create_action_node_params),
    "decision": ("❓ Decision", create_decision_node_params),
}
