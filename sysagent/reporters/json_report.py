import json
import socket
from datetime import datetime
from typing import Dict, Any

def generate_json(data: Dict[str, Any], model_used: str = "gemini-2.0-flash") -> str:
    """Generates structured JSON content containing system scan data and metadata."""
    report = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "hostname": socket.gethostname(),
            "sysagent_version": "0.1.0",
            "model_used": model_used
        },
        "system_data": data
    }
    return json.dumps(report, indent=4, default=str)
