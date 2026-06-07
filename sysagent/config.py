import os
import sys
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import keyring

# Support python 3.11+ natively, or fallback to tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Load env variables from .env if present
load_dotenv()

logger = logging.getLogger("sysagent.config")

@dataclass
class Config:
    model: str = "gemini-2.0-flash"
    read_only_mode: bool = True
    cache_ttl_seconds: int = 30
    log_level: str = "INFO"
    max_history_turns: int = 20
    
    # Alert Thresholds
    cpu_usage_pct: float = 90.0
    memory_usage_pct: float = 85.0
    disk_usage_pct: float = 90.0
    battery_pct: float = 10.0

    @classmethod
    def load(cls) -> "Config":
        """Loads configuration from ~/.sysagent/config.toml, falling back to defaults."""
        home = os.path.expanduser("~")
        config_dir = os.path.join(home, ".sysagent")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.toml")
        
        if not os.path.exists(config_path):
            # Write default config to file to make it transparent
            default_config = cls()
            default_config.save()
            return default_config

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            
            # Map values
            return cls(
                model=data.get("model", "gemini-2.0-flash"),
                read_only_mode=data.get("read_only_mode", True),
                cache_ttl_seconds=data.get("cache_ttl_seconds", 30),
                log_level=data.get("log_level", "INFO"),
                max_history_turns=data.get("max_history_turns", 20),
                cpu_usage_pct=data.get("alerts", {}).get("cpu_usage_pct", 90.0),
                memory_usage_pct=data.get("alerts", {}).get("memory_usage_pct", 85.0),
                disk_usage_pct=data.get("alerts", {}).get("disk_usage_pct", 90.0),
                battery_pct=data.get("alerts", {}).get("battery_pct", 10.0),
            )
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}, using defaults. Error: {e}")
            return cls()

    def save(self) -> None:
        """Saves current configuration to ~/.sysagent/config.toml."""
        home = os.path.expanduser("~")
        config_dir = os.path.join(home, ".sysagent")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.toml")
        
        toml_content = f"""# SysAgent Configuration File

model = "{self.model}"
read_only_mode = {str(self.read_only_mode).lower()}
cache_ttl_seconds = {self.cache_ttl_seconds}
log_level = "{self.log_level}"
max_history_turns = {self.max_history_turns}

[alerts]
cpu_usage_pct = {self.cpu_usage_pct}
memory_usage_pct = {self.memory_usage_pct}
disk_usage_pct = {self.disk_usage_pct}
battery_pct = {self.battery_pct}
"""
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(toml_content)
        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")


def get_api_key() -> Optional[str]:
    """Retrieves the Gemini API Key from keyring or environment variables."""
    # 1. Check keyring
    try:
        key = keyring.get_password("sysagent", "GEMINI_API_KEY")
        if key:
            return key
    except Exception as e:
        logger.debug(f"Failed to fetch key from keyring: {e}")

    # 2. Check environment variables
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key

    return None

def set_api_key(key: str) -> bool:
    """Saves the Gemini API Key into the secure keyring database."""
    try:
        keyring.set_password("sysagent", "GEMINI_API_KEY", key)
        return True
    except Exception as e:
        logger.error(f"Failed to write key to keyring: {e}")
        # If keyring fails, write to a private env file as a fallback, but the rules state:
        # "NEVER store GEMINI_API_KEY in a plain text file — use keyring"
        # So we should return False if keyring fails, prompting user instructions.
        return False

def print_key_missing_instructions():
    """Prints a clear missing API key warning message."""
    print("=" * 60)
    print("No Gemini API key found.")
    print("Get a FREE key at: https://aistudio.google.com/app/apikey")
    print("Then run:")
    print("  sysagent config set GEMINI_API_KEY <your-key>")
    print("=" * 60)
