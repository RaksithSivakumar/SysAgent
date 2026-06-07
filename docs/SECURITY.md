# Security & Privacy Policy - SysAgent

## 1. Data Collection & Isolation
All hardware and software information gathered by SysAgent's collectors remains **entirely local on your computer**. 
- Telemetry data is never uploaded to any remote servers, databases, or third-party loggers.
- The rotating logs are stored locally at `~/.sysagent/sysagent.log`.
- Local scan history snapshots are stored at `~/.sysagent/snapshots/`.
- Encryption keys are stored with restricted permissions at `~/.sysagent/keystore`.

---

## 2. What Data is Sent to Gemini?
When you use `sysagent ask` or `sysagent chat`, SysAgent sends **only the structured output of the relevant collectors** to the Google Gemini API.
- **No Raw Files:** SysAgent never reads or uploads contents of your personal files, documents, codebases, or browser data.
- **No Credentials:** Environment variables are strictly filtered to exclude any keys indicating tokens, secrets, or passwords.
- **Local Context only:** The model only has context on the system's hardware capabilities, active processes names, and network layouts.

---

## 3. How to Run in Fully Offline Mode (Ollama integration)
If you require strict offline execution or want to avoid external API calls:
1. Install [Ollama](https://ollama.com/) on your local machine.
2. Download a lightweight local model:
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
3. Update the configuration to direct requests to your local Ollama endpoint:
   - SysAgent supports custom model endpoints. Swap to Ollama by updating config parameters inside `~/.sysagent/config.toml` (e.g. setting custom model hooks or custom local wrappers).
   - Alternatively, you can disable the AI functionality entirely and use `sysagent scan` or `sysagent watch`, which run **100% locally** and never require an internet connection or an API key.

---

## 4. Reporting a Vulnerability
If you discover a security vulnerability or exploit inside SysAgent, please do not file a public GitHub issue. 

Instead, report it privately to the maintainers or send an email describing the vulnerability, a proof of concept (PoC), and steps to reproduce. We will coordinate a security patch and release updates.
