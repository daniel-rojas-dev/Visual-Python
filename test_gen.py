import sys
from codegen.code_generator import CodeGenerator

def main():
    canvas = {
        "views": {
            "Main": {
                "widgets": {
                    "btn1": {"type": "CTkButton", "rx": 0.5, "ry": 0.5, "rw": 0.2, "rh": 0.1, "props": {"text": "Click", "view": "Main"}},
                    "lbl1": {"type": "CTkLabel", "rx": 0.1, "ry": 0.1, "rw": 0.2, "rh": 0.1, "props": {"text": "Hello", "view": "Main"}}
                }
            },
            "View_2": {
                "widgets": {
                    "btn2": {"type": "CTkButton", "rx": 0.5, "ry": 0.5, "rw": 0.2, "rh": 0.1, "props": {"text": "Go Back", "view": "View_2"}}
                }
            }
        }
    }
    
    nodes = {
        "nodes": {
            "event_1": {"node_type": "event", "id": "event_1", "params": {"trigger": "Click", "var_name": "btn1"}},
            "action_1": {"node_type": "action", "id": "action_1", "params": {"action": "change_view", "view_name": "View_2"}},
            "event_2": {"node_type": "event", "id": "event_2", "params": {"trigger": "Click", "var_name": "btn2"}},
            "action_2": {"node_type": "action", "id": "action_2", "params": {"action": "change_view", "view_name": "Main"}}
        },
        "connections": [
            {"from_node": "event_1", "from_port": "trigger", "to_node": "action_1", "to_port": "trigger"},
            {"from_node": "event_2", "from_port": "trigger", "to_node": "action_2", "to_port": "trigger"}
        ]
    }
    
    cg = CodeGenerator()
    code = cg.generate(canvas, nodes)
    
    with open("generated_preview.py", "w", encoding="utf-8") as f:
        f.write(code)
    
    print("Done")

if __name__ == "__main__":
    main()
