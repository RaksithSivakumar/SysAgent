import os
import json
import logging
import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("sysagent.agent.memory")

class ConversationMemory:
    """Wraps Gemini's chat session to export histories."""
    def __init__(self, chat_session: Any):
        self.chat = chat_session

    def export_chat_history(self) -> List[Dict[str, str]]:
        """Extracts history from the active chat session into standard {role, text} format."""
        history = []
        if not self.chat or not hasattr(self.chat, "history"):
            return history

        for msg in self.chat.history:
            role = "user" if msg.role == "user" else "agent"
            text_parts = []
            for part in msg.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
                elif hasattr(part, "function_call") and part.function_call.name:
                    text_parts.append(f"[Call: {part.function_call.name}]")
                elif hasattr(part, "function_response") and part.function_response.name:
                    text_parts.append(f"[Response: {part.function_response.name}]")
            
            history.append({
                "role": role,
                "text": " ".join(text_parts).strip()
            })
        return history

def _get_snapshots_dir() -> str:
    home = os.path.expanduser("~")
    snap_dir = os.path.join(home, ".sysagent", "snapshots")
    os.makedirs(snap_dir, exist_ok=True)
    return snap_dir

def save_snapshot(data: Dict[str, Any]) -> str:
    """Saves a timestamped system metrics snapshot to ~/.sysagent/snapshots/."""
    snap_dir = _get_snapshots_dir()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"snapshot_{timestamp}.json"
    file_path = os.path.join(snap_dir, filename)
    
    try:
        # Include custom timestamp metadata
        snapshot = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "data": data
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=4, default=str)
        logger.info(f"Snapshot written to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to write system snapshot: {e}")
        raise e

def list_snapshots() -> List[Dict[str, Any]]:
    """Lists all available snapshots saved in ~/.sysagent/snapshots/."""
    snap_dir = _get_snapshots_dir()
    snapshots = []
    if not os.path.exists(snap_dir):
        return snapshots

    try:
        for entry in os.scandir(snap_dir):
            if entry.is_file() and entry.name.startswith("snapshot_") and entry.name.endswith(".json"):
                snapshots.append({
                    "filename": entry.name,
                    "path": entry.path,
                    "created": datetime.datetime.fromtimestamp(entry.stat().st_mtime).isoformat()
                })
    except Exception as e:
        logger.error(f"Failed to list snapshots: {e}")
        
    return sorted(snapshots, key=lambda x: x["filename"], reverse=True)

def compare_snapshots(snap1_path: str, snap2_path: str) -> Dict[str, Any]:
    """Compares two snapshots and generates a dictionary details of changes."""
    logger.info(f"Comparing snapshots {snap1_path} vs {snap2_path}")
    diffs: Dict[str, Any] = {
        "cpu_usage_change_pct": 0.0,
        "ram_usage_change_pct": 0.0,
        "new_processes": [],
        "terminated_processes": [],
        "new_exposed_ports": [],
        "closed_exposed_ports": [],
        "uptime_change_str": ""
    }

    try:
        with open(snap1_path, "r", encoding="utf-8") as f:
            s1 = json.load(f)
        with open(snap2_path, "r", encoding="utf-8") as f:
            s2 = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load snapshots for comparison: {e}")
        return {"error": f"Failed to load files: {str(e)}"}

    d1 = s1.get("data", {})
    d2 = s2.get("data", {})

    # 1. CPU / RAM Deltas
    try:
        cpu1 = d1.get("get_cpu_info", {}).get("usage_overall_pct", 0.0)
        cpu2 = d2.get("get_cpu_info", {}).get("usage_overall_pct", 0.0)
        diffs["cpu_usage_change_pct"] = round(cpu2 - cpu1, 2)
    except Exception:
        pass

    try:
        ram1 = d1.get("get_memory_info", {}).get("ram_usage_pct", 0.0)
        ram2 = d2.get("get_memory_info", {}).get("ram_usage_pct", 0.0)
        diffs["ram_usage_change_pct"] = round(ram2 - ram1, 2)
    except Exception:
        pass

    # 2. Processes checks
    try:
        p1 = {p.get("pid"): p.get("name") for p in d1.get("get_processes", {}).get("top_cpu", [])}
        p2 = {p.get("pid"): p.get("name") for p in d2.get("get_processes", {}).get("top_cpu", [])}
        
        # Merge top cpu + top memory to construct processes set
        p1.update({p.get("pid"): p.get("name") for p in d1.get("get_processes", {}).get("top_memory", [])})
        p2.update({p.get("pid"): p.get("name") for p in d2.get("get_processes", {}).get("top_memory", [])})

        new_pids = set(p2.keys()) - set(p1.keys())
        term_pids = set(p1.keys()) - set(p2.keys())

        diffs["new_processes"] = [f"{p2[pid]} (PID {pid})" for pid in new_pids if pid]
        diffs["terminated_processes"] = [f"{p1[pid]} (PID {pid})" for pid in term_pids if pid]
    except Exception:
        pass

    # 3. exposed inbound ports
    try:
        port1 = {p.get("port") for p in d1.get("get_firewall_info", {}).get("listening_ports", [])}
        port2 = {p.get("port") for p in d2.get("get_firewall_info", {}).get("listening_ports", [])}

        new_ports = port2 - port1
        closed_ports = port1 - port2

        diffs["new_exposed_ports"] = sorted(list(new_ports))
        diffs["closed_exposed_ports"] = sorted(list(closed_ports))
    except Exception:
        pass

    # 4. Uptime diff
    try:
        u1 = d1.get("get_os_info", {}).get("uptime_seconds", 0)
        u2 = d2.get("get_os_info", {}).get("uptime_seconds", 0)
        diff_s = int(u2 - u1)
        if diff_s > 0:
            diffs["uptime_change_str"] = f"+ {diff_s // 60}m {diff_s % 60}s elapsed"
        else:
            diffs["uptime_change_str"] = "System rebooted or elapsed time negative"
    except Exception:
        pass

    return diffs
