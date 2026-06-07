from sysagent.security.sandbox import SandboxedCollector

# Import all collector functions
from sysagent.collectors.cpu import get_cpu_info
from sysagent.collectors.memory import get_memory_info
from sysagent.collectors.disk import get_disk_info
from sysagent.collectors.gpu import get_gpu_info
from sysagent.collectors.network import get_network_info
from sysagent.collectors.battery import get_battery_info
from sysagent.collectors.os_info import get_os_info
from sysagent.collectors.processes import get_processes
from sysagent.collectors.software import get_software_info

def register_all_collectors(sandbox: SandboxedCollector) -> None:
    """Registers all default hardware and software collectors into the sandbox."""
    sandbox.register_collector("get_cpu_info", get_cpu_info)
    sandbox.register_collector("get_memory_info", get_memory_info)
    sandbox.register_collector("get_disk_info", get_disk_info)
    sandbox.register_collector("get_gpu_info", get_gpu_info)
    sandbox.register_collector("get_network_info", get_network_info)
    sandbox.register_collector("get_battery_info", get_battery_info)
    sandbox.register_collector("get_os_info", get_os_info)
    sandbox.register_collector("get_processes", get_processes)
    sandbox.register_collector("get_software_info", get_software_info)
