# 🖥️ Numbers10 PCMonitor Pro

> **Enterprise-grade PC monitoring platform by Numbers10 Technology Solutions**
> Multi-company | Read-only probes | Real-time alerts | Self-hosted VPS

---

## 📋 Table of Contents
- [Architecture Overview](#architecture-overview)
- [Port Assignments](#port-assignments)
- [Quick VPS Deploy](#quick-vps-deploy)
- [Adding a New Client Company](#adding-a-new-client-company)
- [Installing the Probe on a Client PC](#installing-the-probe-on-a-client-pc)
- [Building a Company-Specific Probe EXE](#building-a-company-specific-probe-exe)
- [Environment Variables](#environment-variables)
- [Default Admin Credentials](#default-admin-credentials)
- [Versioning](#versioning)

---

## 🏗️ Architecture Overview

```
[Client PC - Company A]  →  Probe Agent (Windows Service)  ─┐
[Client PC - Company A]  →  Probe Agent (Windows Service)  ─┤
[Client PC - Company B]  →  Probe Agent (Windows Service)  ─┼──► VPS :8443 (nginx)
[Client PC - Company B]  →  Probe Agent (Windows Service)  ─┤       ↓
[Client PC - Company C]  →  Probe Agent (Windows Service)  ─┘   FastAPI :8888
                                                                      ↓
                                                              PostgreSQL :5433
                                                                      ↓
                                                          Admin Dashboard (React)
```

**Three components:**
1. `backend/` — FastAPI + PostgreSQL + TimescaleDB on your VPS
2. `probe/` — Python Windows Service compiled to `.exe`, installed on client PCs
3. `frontend/` — React dashboard, admin-only, served via nginx

---

## 🔌 Port Assignments

| Service | Port | Public? | Notes |
|---------|------|---------|-------|
| Nginx (dashboard entry) | **8443** | ✅ Yes | Only port to open in UFW |
| FastAPI backend | 8888 | 🔒 Internal | Proxied by nginx only |
| React frontend | 3030 | 🔒 Internal | Proxied by nginx only |
| PostgreSQL | 5433 | 🔒 Localhost | Never exposed publicly |

> **Does NOT conflict with:** `22, 80, 443, 8080, 8081`

---

## 🚀 Quick VPS Deploy

```bash
# 1. Clone the repo
git clone https://github.com/Joevikingroux/monitorpro.git
cd monitorpro

# 2. Run the one-command setup script
chmod +x setup.sh
./setup.sh

# 3. Dashboard will be live at:
#    https://YOUR-VPS-IP:8443
```

The `setup.sh` script will:
- Install Docker + Docker Compose if not present
- Prompt you to set passwords and keys
- Generate a self-signed SSL cert if none exists
- Build and start all containers
- Open UFW port 8443

---

## 🏢 Adding a New Client Company

1. Log into the dashboard at `https://YOUR-VPS-IP:8443`
2. Navigate to **Companies** → **+ Add Company**
3. Fill in: Company name, contact name, contact email
4. Click **Create** — a unique **Company Token** is generated
5. Click **Copy Token** — you'll use this for the probe installer

---

## 🖥️ Installing the Probe on a Client PC

### Option A — Config file (flexible)
1. Copy `probe/config.ini.template` to `config.ini`
2. Set `company_token = YOUR_COMPANY_TOKEN`
3. Set `url = https://YOUR-VPS-IP:8443`
4. Place `config.ini` in the same folder as `PCMonitorProbe_Setup.exe`
5. Run `PCMonitorProbe_Setup.exe` as Administrator
6. PC appears in dashboard within 30 seconds ✅

### Option B — Baked-in token EXE (easiest for clients)
See section below — the token is compiled into the EXE, no config file needed.

### To uninstall the probe from a PC
```
PCMonitorProbe_Setup.exe uninstall
```

---

## 🔨 Building a Company-Specific Probe EXE

```bat
cd probe
build_exe.bat COMPANY_TOKEN=your_token_here SERVER_URL=https://YOUR-VPS-IP:8443
```

This produces `dist/PCMonitorProbe_Setup.exe` with the token and server URL
baked in — the client just runs it once and it works with zero configuration.

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_PASSWORD` | PostgreSQL password | *(set a strong password)* |
| `SECRET_KEY` | JWT signing key (min 32 chars random) | `openssl rand -hex 32` |
| `ADMIN_EMAIL` | Initial admin login email | *(your email address)* |
| `ADMIN_PASSWORD` | Initial admin password (change after first login) | *(set a strong password)* |
| `SMTP_HOST` | SMTP server for email alerts | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | SMTP username | *(your SMTP email)* |
| `SMTP_PASSWORD` | SMTP password | *(your app password)* |
| `SMTP_FROM` | From address for alert emails | `PCMonitor <your@email.com>` |
| `TELEGRAM_TOKEN` | Telegram bot token for alerts | *(from @BotFather)* |
| `DOMAIN` | Your VPS domain or IP | `monitor.yourdomain.com` |
| `RETENTION_DAYS` | Days to keep metric data | `90` |

---

## 🔐 Default Admin Credentials

```
Email:    set via ADMIN_EMAIL in your .env file
Password: set via ADMIN_PASSWORD in your .env file
```

> **Change your password immediately after first login via Settings → Profile.**

---

## 📦 Versioning

This project uses **semantic versioning**: `MAJOR.MINOR.PATCH`

| Version | What changed |
|---------|-------------|
| v1.0.0 | Initial release — backend, probe, frontend, multi-company |

See [CHANGELOG.md](CHANGELOG.md) for full history.

---

## 🏷️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy 2.x async, Alembic, APScheduler |
| Database | PostgreSQL 16 + TimescaleDB |
| Probe | Python 3.10+, psutil, wmi, pywin32, PyInstaller |
| Frontend | React 18, Vite, TailwindCSS, Recharts, Zustand |
| Reverse proxy | Nginx |
| Containerisation | Docker + Docker Compose |

---

*Numbers10 Technology Solutions — Your IT. Sorted.*
