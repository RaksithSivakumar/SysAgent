# SysAgent — AI-Powered System Intelligence Agent

SysAgent is a production-grade, AI-powered system intelligence CLI tool that communicates with your host computer's hardware and software configurations, audits security postures, generates dashboards, and lets you chat with your system in real time using Google Gemini.

![SysAgent Interactive Chat Session](sysagent_repl.png)

> [!NOTE]
> **FREE to use** — fully powered by Google Gemini's free tier (gemini-2.0-flash).

---

## 🚀 Installation

Install directly via `pip` (requires Python 3.11+):

```bash
pip install sysagent
```

---

## 🔑 Getting Started

1. **Get a free Gemini API Key:**
   Visit [Google AI Studio API Key Manager](https://aistudio.google.com/app/apikey) to generate a free key (no credit card required).

2. **Configure your API Key:**
   Save the key securely into your system's keyring manager:
   ```bash
   sysagent config set GEMINI_API_KEY <your-api-key>
   ```

---

## ⚡ Quick Start: 5 Common Commands

### 1. Perform a Full System Scan
Gathers CPU, RAM, Partition layouts, connections, network interfaces, and highlights warnings.
```bash
sysagent scan
```

### 2. Query System Status using Natural Language
Ask specific questions about your hardware configuration or processes:
```bash
sysagent ask "How much free RAM do I have right now?"
```
*Expected Output:*
> You have 8.42 GB of free physical RAM out of 16.0 GB total (47.3% used).

### 3. Open Interactive REPL Dialogue Chat
Start an interactive chat session with the Gemini brain:
```bash
sysagent chat
```

### 4. Open Live Watch Dashboard (TUI)
Run a live status terminal dashboard that refreshes every 5 seconds:
```bash
sysagent watch
```
*(Press Q to exit)*

### 5. Generate and Save a Premium HTML Report
Create a beautiful, single-file HTML report summarizing system parameters:
```bash
sysagent report --format html --save ./report.html
```
*(Pass `--encrypt` to encrypt the file symmetrically)*

---

## 🛠️ Configuration Options

Configuration is stored in `~/.sysagent/config.toml`. You can modify it using:
```bash
sysagent config set <parameter> <value>
```

Supported config keys:
- `model`: Gemini model (default `gemini-2.0-flash`, fallback `gemini-1.5-pro`)
- `read_only_mode`: Set to `true` to block any destructive system changes.
- `cache_ttl_seconds`: Duration in seconds to cache telemetry outputs.
- `alert.cpu_threshold`: CPU usage warning limit in % (default `90`)
- `alert.memory_threshold`: RAM usage warning limit in % (default `85`)
- `alert.disk_threshold`: Disk partition warning limit in % (default `90`)
- `alert.battery_threshold`: Battery warning limit in % (default `10`)

---

## 🛡️ Security & Sandboxing Model

- **Read-Only by Default:** SysAgent operates under a strict sandboxed execution layer (`SandboxedCollector`). It will abort any action that attempts to modify files, packages, or settings.
- **Audit Logs:** Every telemetry collection is audited. Records containing timestamps, command names, executing user, and byte size are saved to `~/.sysagent/audit.log`.
- **Encrypted Storage:** Reports generated using the `--encrypt` flag are encrypted using AES symmetric Fernet encryption. Keys are stored with limited owner-read privileges (`0600`) at `~/.sysagent/keystore`.
- **No Credentials Leaked:** Environment scans strictly filter out any keys containing terms like `PASS`, `KEY`, `SECRET`, or `TOKEN`.

---

## 📊 Free Tier Limits

SysAgent uses the default model `gemini-2.0-flash` on the free tier:
- **Rate Limit:** 15 Requests Per Minute (RPM)
- **Daily Limit:** 1,500 Requests Per Day
- **Full Scans:** Limited to maximum 1 scan per 60 seconds to prevent resource exhaustion.
