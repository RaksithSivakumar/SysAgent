import logging
from dataclasses import dataclass
from typing import List, Dict, Any
from sysagent.config import Config

logger = logging.getLogger("sysagent.reporters.alert")

@dataclass
class Alert:
    level: str  # WARNING, CRITICAL, INFO
    message: str
    value: Any

class AlertEngine:
    def __init__(self, config: Config, data: Dict[str, Any]):
        self.config = config
        self.data = data

    def check_all(self) -> List[Alert]:
        """Runs all resource and network port vulnerability checks."""
        alerts: List[Alert] = []
        
        # 1. CPU usage check
        cpu_data = self.data.get("get_cpu_info", {})
        cpu_usage = cpu_data.get("usage_overall_pct")
        if cpu_usage is not None and isinstance(cpu_usage, (int, float)):
            if cpu_usage > self.config.cpu_usage_pct:
                alerts.append(Alert(
                    level="WARNING",
                    message=f"CPU usage is high: {cpu_usage}% (threshold {self.config.cpu_usage_pct}%)",
                    value=cpu_usage
                ))

        # 2. Memory usage check
        mem_data = self.data.get("get_memory_info", {})
        ram_usage = mem_data.get("ram_usage_pct")
        if ram_usage is not None and isinstance(ram_usage, (int, float)):
            if ram_usage > self.config.memory_usage_pct:
                alerts.append(Alert(
                    level="WARNING",
                    message=f"Memory RAM usage is high: {ram_usage}% (threshold {self.config.memory_usage_pct}%)",
                    value=ram_usage
                ))

        # 3. Disk partitions check
        disk_data = self.data.get("get_disk_info", {})
        for part in disk_data.get("partitions", []):
            usage = part.get("usage_pct")
            mount = part.get("mountpoint", "Unknown mount")
            if usage is not None and isinstance(usage, (int, float)):
                if usage > self.config.disk_usage_pct:
                    alerts.append(Alert(
                        level="CRITICAL",
                        message=f"Disk partition '{mount}' is near capacity: {usage}% (threshold {self.config.disk_usage_pct}%)",
                        value=usage
                    ))

        # 4. Battery capacity check
        bat_data = self.data.get("get_battery_info", {})
        if bat_data.get("present"):
            charge = bat_data.get("charge_pct")
            status = bat_data.get("status", "")
            if charge is not None and isinstance(charge, (int, float)):
                if charge < self.config.battery_pct and "discharge" in status.lower():
                    alerts.append(Alert(
                        level="WARNING",
                        message=f"Battery level is low: {charge}% (threshold {self.config.battery_pct}%) and discharging",
                        value=charge
                    ))

        # 5. Open Inbound socket ports check
        firewall_data = self.data.get("get_firewall_info", {})
        for p in firewall_data.get("listening_ports", []):
            if p.get("exposed_warning"):
                alerts.append(Alert(
                    level="WARNING",
                    message=p.get("warning_reason", f"Exposed port {p.get('port')} on {p.get('address')}"),
                    value=p.get("port")
                ))

        # 6. Unsafe world writable files check
        sec_data = self.data.get("get_security_audit", {})
        for uf in sec_data.get("world_writable_files", []):
            alerts.append(Alert(
                level="CRITICAL",
                message=f"Security risk: world-writable file found: {uf}",
                value=uf
            ))

        return alerts
