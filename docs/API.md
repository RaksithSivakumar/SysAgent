# SysAgent Developer API Reference

This document describes the Python API structure, modules, and schemas used within SysAgent.

---

## 1. Collectors API (`sysagent.collectors`)

Every collector function takes no arguments and returns a standard Python dictionary (`Dict[str, Any]`).

### CPU Info (`sysagent.collectors.cpu.get_cpu_info`)
Returns processor architecture, model name, cache details, and live loads.
```python
{
    "model": "Intel Core i7-10700K",
    "architecture": "X86_64",
    "socket": "LGA1200",
    "physical_cores": 8,
    "logical_cores": 16,
    "frequency_current_mhz": 3800.0,
    "frequency_min_mhz": 800.0,
    "frequency_max_mhz": 5100.0,
    "usage_per_core_pct": [12.1, 15.4, ...],
    "usage_overall_pct": 14.2,
    "temperature_c": 45.0,
    "cache_l1_data": "256 KB",
    "cache_l1_instruction": "256 KB",
    "cache_l2": "2 MB",
    "cache_l3": "16 MB"
}
```

### Memory Info (`sysagent.collectors.memory.get_memory_info`)
Returns RAM specs, swaps, speeds and type flags.
```python
{
    "ram_total_bytes": 17179869184,
    "ram_available_bytes": 8589934592,
    "ram_used_bytes": 8589934592,
    "ram_usage_pct": 50.0,
    "swap_total_bytes": 4294967296,
    "swap_used_bytes": 1073741824,
    "swap_free_bytes": 3221225472,
    "swap_usage_pct": 25.0,
    "speed_mhz": "3200 MHz",
    "type": "DDR4"
}
```

---

## 2. Security & Sandbox API (`sysagent.security`)

### Sandboxed Collector (`sysagent.security.sandbox.SandboxedCollector`)
Wraps metrics execution, checking read-only permissions and logging actions.
```python
from sysagent.security.sandbox import SandboxedCollector
from sysagent.config import Config

config = Config.load()
sandbox = SandboxedCollector(config)

# Register a function
sandbox.register_collector("get_cpu_info", get_cpu_info)

# Call securely
result = sandbox.call_tool("get_cpu_info")
```

### Report Encryption (`sysagent.security.encryption`)
```python
from sysagent.security.encryption import encrypt_data, decrypt_data, encrypt_file, decrypt_report

# Encrypt string content
encrypted_bytes = encrypt_data("Cleartext Report")

# Decrypt ciphertext
decrypted_str = decrypt_data(encrypted_bytes)

# Encrypt write direct to path
encrypt_file("./report.enc", "Content details")

# Decrypt read from path
raw_json = decrypt_report("./report.enc")
```

---

## 3. Configuration Module (`sysagent.config`)
Handles config serialization (`config.toml`) and secret keyring retrieval.
```python
from sysagent.config import Config, get_api_key, set_api_key

# Load active configuration
config = Config.load()
print(config.cpu_usage_pct) # 90.0

# Store Gemini API Key safely in platform keyring
set_api_key("AIzaSy...")

# Retrieve API key
key = get_api_key()
```
