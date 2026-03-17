# 🖥️ Numbers10 PCMonitor — Claude Code Master Build Prompt

> **Paste this entire prompt into Claude Code to build the full system.**
> Claude Code will generate all files, folders, configs, and code end-to-end.
> The company branding is **Numbers10 Technology Solutions**.
> The logo file is `logo.png` — place it in `frontend/public/logo.png` and
> reference it everywhere specified below.

---

## 🎯 Project Overview

Build **Numbers10 PCMonitor** — a full-stack, enterprise-grade PC monitoring platform
inspired by PRTG, Zabbix, and Datadog, custom-built for a managed IT service
provider (MSP) running on a self-hosted VPS. The system consists of three
independently deployable components:

1. **Backend API Server** — FastAPI + PostgreSQL + TimescaleDB
2. **Windows Probe Agent** — Python Windows Service using `psutil` + `wmi`
3. **Admin Frontend Dashboard** — React + Recharts + TailwindCSS

The admin (Joe) logs into the dashboard and monitors all registered client PCs
in real time, with full alert management and historical graphing. The system is
read-only by design — the probe pushes data to the server, but the server never
pushes commands back to client machines.

---

## 🏗️ Full Project Structure

Generate the following directory layout in full:

```
pcmonitor/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── database.py        # Async SQLAlchemy + PostgreSQL
│   │   │   ├── security.py        # JWT auth, bcrypt, API key generation
│   │   │   └── config.py          # Pydantic Settings from .env
│   │   ├── models/
│   │   │   ├── user.py            # Admin user model
│   │   │   ├── machine.py         # Registered client machine model
│   │   │   ├── metric.py          # Time-series metric snapshots
│   │   │   ├── alert.py           # Alert rules + alert events
│   │   │   └── event_log.py       # Windows Event Log entries
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── machine.py
│   │   │   ├── metric.py
│   │   │   └── alert.py
│   │   ├── api/
│   │   │   ├── auth.py            # POST /login, POST /refresh
│   │   │   ├── machines.py        # CRUD + registration endpoint
│   │   │   ├── metrics.py         # Ingest + query metrics
│   │   │   ├── alerts.py          # Alert rules + events CRUD
│   │   │   └── reports.py         # Export CSV/PDF reports
│   │   └── services/
│   │       ├── alert_engine.py    # APScheduler threshold checks
│   │       ├── notifier.py        # Email + Telegram notifications
│   │       ├── retention.py       # Old metric pruning job
│   │       └── topology.py        # Network topology/auto-discovery
│   ├── alembic/                   # DB migrations
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── .env.example
│
├── probe/
│   ├── probe_agent.py             # Main Windows Service entry point
│   ├── collectors/
│   │   ├── cpu.py                 # CPU usage, per-core, frequency, temp
│   │   ├── memory.py              # RAM, virtual memory, swap
│   │   ├── disk.py                # All drives: usage, SMART health, I/O
│   │   ├── network.py             # Interfaces, bandwidth, latency, MAC
│   │   ├── processes.py           # Top processes by CPU/RAM
│   │   ├── services.py            # Windows Services status
│   │   ├── event_logs.py          # Windows Event Log (Error/Warning)
│   │   ├── hardware.py            # Temps, fan speeds via WMI/OpenHardwareMonitor
│   │   ├── software.py            # Installed software inventory
│   │   └── security.py            # Firewall state, AV status, Windows Update
│   ├── config.ini                 # Server URL, API key, intervals
│   ├── installer.py               # Self-install as Windows Service
│   ├── requirements.txt
│   └── build_exe.bat              # PyInstaller build script
│
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   ├── api/
    │   │   └── client.js          # Axios instance with JWT interceptors
    │   ├── hooks/
    │   │   ├── useMetrics.js      # Polling hook with WebSocket fallback
    │   │   ├── useMachines.js
    │   │   └── useAlerts.js
    │   ├── pages/
    │   │   ├── Login.jsx
    │   │   ├── Dashboard.jsx      # Overview: all machines grid
    │   │   ├── MachineDetail.jsx  # Single machine deep-dive
    │   │   ├── Alerts.jsx         # Alert rules + event history
    │   │   ├── Reports.jsx        # Generate + download reports
    │   │   └── Settings.jsx       # Admin settings, thresholds
    │   └── components/
    │       ├── MachineCard.jsx    # Status card with spark lines
    │       ├── MetricGauge.jsx    # Animated arc gauge
    │       ├── LiveChart.jsx      # Recharts time-series chart
    │       ├── AlertBadge.jsx
    │       ├── Sidebar.jsx
    │       └── Navbar.jsx
    ├── index.html
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.js
```

---

## ⚙️ Backend — Detailed Requirements

### Tech Stack
- **FastAPI** (async) with **Uvicorn**
- **PostgreSQL** with **asyncpg** driver
- **SQLAlchemy 2.x** async ORM
- **Alembic** for migrations
- **APScheduler** for background alert engine
- **Passlib + python-jose** for auth
- **aiosmtplib** for email, **httpx** for Telegram bot alerts
- **Pydantic v2** for all schemas

### Database Models

#### `machines` table
```
id, hostname, display_name, api_key (hashed), os_version, cpu_model,
total_ram_gb, ip_address, mac_address, last_seen, is_online,
registered_at, group_tag, notes
```

#### `metrics` table (time-series, partition by week)
```
id, machine_id, collected_at,
cpu_percent, cpu_freq_mhz, cpu_temp_c,
ram_percent, ram_used_gb, ram_total_gb,
disk_usage (JSONB: [{drive, used_gb, total_gb, percent, read_mb, write_mb}]),
net_sent_mb, net_recv_mb, net_latency_ms,
top_processes (JSONB: [{name, pid, cpu_pct, ram_mb}]),
gpu_percent, gpu_temp_c, gpu_vram_used_mb
```

#### `alert_rules` table
```
id, name, machine_id (nullable = applies to all), metric_field,
operator (gt/lt/eq), threshold, duration_seconds,
severity (info/warning/critical), enabled,
notify_email, notify_telegram
```

#### `alert_events` table
```
id, rule_id, machine_id, triggered_at, resolved_at,
current_value, message, acknowledged, acknowledged_by
```

#### `windows_services` table
```
id, machine_id, service_name, display_name, status,
startup_type, last_checked
```

#### `software_inventory` table
```
id, machine_id, name, version, publisher, install_date, scanned_at
```

#### `event_logs` table
```
id, machine_id, log_source, event_id, level, message, occurred_at
```

### API Endpoints

#### Auth
- `POST /api/auth/login` — returns JWT access + refresh token
- `POST /api/auth/refresh` — refresh access token
- `POST /api/auth/change-password`

#### Machines
- `POST /api/machines/register` — probe self-registers with machine info (API key auth)
- `GET /api/machines` — list all machines with latest metric snapshot
- `GET /api/machines/{id}` — full machine detail
- `PATCH /api/machines/{id}` — update display name, group, notes
- `DELETE /api/machines/{id}`
- `GET /api/machines/{id}/services` — Windows services list
- `GET /api/machines/{id}/software` — installed software
- `GET /api/machines/{id}/event-logs` — Windows event log entries

#### Metrics
- `POST /api/metrics/ingest` — probe POSTs metric snapshot (API key auth)
- `GET /api/metrics/{machine_id}?from=&to=&interval=` — historical data
- `GET /api/metrics/{machine_id}/latest` — most recent snapshot
- `GET /api/metrics/{machine_id}/processes` — current top processes

#### Alerts
- `GET /api/alerts/rules` — list all alert rules
- `POST /api/alerts/rules` — create alert rule
- `PATCH /api/alerts/rules/{id}` — update
- `DELETE /api/alerts/rules/{id}`
- `GET /api/alerts/events` — alert event history (filter by machine, severity, date)
- `POST /api/alerts/events/{id}/acknowledge` — admin acknowledges alert
- `GET /api/alerts/events/unresolved` — active alert count for badge

#### Reports
- `GET /api/reports/machine/{id}?from=&to=` — returns CSV download
- `GET /api/reports/alerts?from=&to=` — alert summary CSV

### Alert Engine (APScheduler)
- Runs every **30 seconds** as a background job
- For each enabled alert rule, queries the latest metric for matching machines
- Evaluates: `current_value {operator} threshold` — e.g. `cpu_percent > 90`
- If breached for `duration_seconds`, creates an `alert_event` record
- Marks machine as `is_online=False` if `last_seen` > 3 minutes ago
- Sends notification via email and/or Telegram bot
- Auto-resolves alert events when metric drops back below threshold

### Notification System
- **Email**: aiosmtplib SMTP, HTML-formatted email with machine name, metric,
  current value, threshold, and a link to the dashboard
- **Telegram**: httpx POST to Bot API with formatted message
- Configurable per alert rule: email + telegram checkboxes

### Data Retention
- Background job runs nightly
- Deletes `metrics` rows older than configurable retention period (default: 90 days)
- Logs pruning stats

---

## 🔌 Windows Probe Agent — Detailed Requirements

### Tech Stack
- **Python 3.10+**
- **psutil** — cross-platform system metrics
- **wmi** — Windows-specific: hardware sensors, services, event logs, software
- **pywin32** — Windows Service integration (`win32serviceutil`, `win32service`)
- **requests** — HTTP POST to backend
- **configparser** — reads `config.ini`
- **logging** — logs to Windows Event Log + local file

### `config.ini` Structure
```ini
[server]
url = https://your-vps.com
api_key = MACHINE_API_KEY_HERE
ingest_interval_seconds = 30

[alerts]
local_alert_log = true

[hardware]
use_open_hardware_monitor = false
```

### Probe Boot Sequence
1. Reads `config.ini`
2. On first run: calls `POST /api/machines/register` with full system info
   (hostname, OS, CPU model, RAM, MAC, IP) — server returns API key stored in config
3. Starts one background thread:
   - **Metric thread**: collects and POSTs every `ingest_interval_seconds`

### Metric Collectors — Full Detail

#### CPU (`collectors/cpu.py`)
- `psutil.cpu_percent(percpu=True)` — overall + per-core
- `psutil.cpu_freq()` — current MHz
- CPU temperature via `wmi` (Win32_TemperatureProbe or OpenHardwareMonitor WMI)
- CPU model string via `wmi` Win32_Processor

#### Memory (`collectors/memory.py`)
- `psutil.virtual_memory()` — total, used, available, percent
- `psutil.swap_memory()` — swap total, used, percent

#### Disk (`collectors/disk.py`)
- `psutil.disk_partitions()` — enumerate all real drives
- `psutil.disk_usage(drive)` — used/total/percent per drive
- `psutil.disk_io_counters(perdisk=True)` — read/write MB per drive
- SMART health status via `wmi` Win32_DiskDrive (Status field)

#### Network (`collectors/network.py`)
- `psutil.net_io_counters(pernic=True)` — bytes sent/recv per interface
- `psutil.net_if_addrs()` — IP and MAC addresses
- Ping latency to backend server using `socket` + `time`
- Active connections count: `psutil.net_connections()`

#### Processes (`collectors/processes.py`)
- `psutil.process_iter(['name','pid','cpu_percent','memory_info','status'])`
- Top 10 by CPU, top 10 by RAM
- Filter out system idle process

#### Windows Services (`collectors/services.py`)
- `wmi` Win32_Service — name, display_name, State, StartMode
- POST full list every 5 minutes (not every 30s)

#### Windows Event Logs (`collectors/event_logs.py`)
- `wmi` Win32_NTLogEvent — filter: EventType IN (1=Error, 2=Warning)
- Last 50 events from System + Application logs
- POST new events only (track last seen event ID)

#### Hardware Sensors (`collectors/hardware.py`)
- CPU temperature: wmi query to OpenHardwareMonitor WMI provider if running
- Fallback: `wmi` Win32_TemperatureProbe
- GPU: if NVIDIA, use `pynvml` (nvidia-ml-py) for GPU util%, temp, VRAM
- Fan speeds via OpenHardwareMonitor WMI

#### Software Inventory (`collectors/software.py`)
- Read Windows Registry: `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`
- Also `HKLM\SOFTWARE\WOW6432Node\...` for 32-bit apps
- Extract: DisplayName, DisplayVersion, Publisher, InstallDate
- POST full list once on startup, then every 24h

#### Security Status (`collectors/security.py`)
- Windows Firewall state: `wmi` NetFwMgr or registry
- Windows Defender/AV status: `wmi` AntiVirusProduct via SecurityCenter2
- Windows Update pending count: `wmi` Win32_QuickFixEngineering
- Last boot time: `wmi` Win32_OperatingSystem.LastBootUpTime

### Windows Service Install
Running `python installer.py install` must:
1. Register probe as a Windows Service named `PCMonitorProbe`
2. Set startup type to Automatic
3. Start the service immediately
4. Log to Windows Event Log under source `PCMonitorProbe`

Running `python installer.py remove` cleanly uninstalls.

### Build to EXE
`build_exe.bat` uses PyInstaller to bundle the probe + all dependencies
into a single `PCMonitorProbe_Setup.exe` that the admin can drop on any
client PC and run once.

---

## 🎨 Frontend Dashboard — Detailed Requirements

### Tech Stack
- **React 18** + **Vite**
- **TailwindCSS** with custom dark theme
- **Recharts** for all charts and sparklines
- **Axios** with JWT interceptor (auto-refresh on 401)
- **React Router v6**
- **Zustand** for global state (machines, alerts, user)
- **React Query (TanStack Query)** for data fetching + caching
- **date-fns** for timestamps
- **lucide-react** for icons

### Branding & Assets

The company is **Numbers10 Technology Solutions**. A logo file `logo.png` is
located in `frontend/public/logo.png`. Use it everywhere appropriate:
- Login page (centered, prominent, ~200px wide)
- Sidebar top (full logo expanded, diamond icon only when collapsed)
- Browser tab favicon reference
- Reports page header
- Email notification templates (as hosted `<img>` URL)

**Do NOT use a text fallback for the logo — always render the image.**

### Design Theme — Exact Numbers10 Website Styles

> These values were extracted directly from www.numbers10.co.za.
> Replicate the exact same look and feel in the dashboard.

```css
:root {
  /* ── Backgrounds (alternating sections like the website) ── */
  --bg-base:        #000000;      /* primary page background - pure black */
  --bg-surface:     #050a12;      /* alternate section bg (rgb 5,10,18) */
  --bg-card:        rgba(10, 18, 32, 0.70); /* card background with transparency */
  --bg-elevated:    #0d1520;      /* hover states, modals, dropdowns */
  --bg-nav:         #000000;      /* navbar background */

  /* ── Numbers10 Teal Accent (exact value from site: rgb 45,212,191) ── */
  --accent-primary:   #2dd4bf;    /* teal-400 — icons, active states, headings */
  --accent-hover:     #14b8a6;    /* teal-500 — hover state */
  --accent-glow:      #2dd4bf;    /* glow effects */
  --accent-subtle:    rgba(45, 212, 191, 0.08);  /* card bg tint */
  --accent-border:    rgba(45, 212, 191, 0.15);  /* subtle card borders */
  --accent-border-solid: rgb(45, 212, 191);       /* strong card borders */

  /* ── CTA Button (exact from site) ── */
  --btn-primary-bg:    #2dd4bf;
  --btn-primary-text:  #000000;   /* black text on teal button */
  --btn-primary-radius: 8px;
  --btn-outline-bg:    transparent;
  --btn-outline-border: rgb(45, 212, 191);
  --btn-outline-text:  #2dd4bf;

  /* ── Typography (exact fonts from site) ── */
  --font-heading:  'Space Grotesk', sans-serif;  /* ALL headings h1-h4 */
  --font-body:     'Inter', system-ui, sans-serif; /* body text, labels, nav */
  --font-mono:     'JetBrains Mono', monospace;    /* metric numbers only */

  /* ── Text Colors (exact from site) ── */
  --text-primary:   rgb(224, 247, 250);  /* h1 color — near white with blue tint */
  --text-secondary: rgb(148, 163, 184);  /* body text — slate-400 */
  --text-muted:     rgb(100, 116, 139);  /* muted labels — slate-500 */
  --text-accent:    #2dd4bf;             /* teal accent text */

  /* ── Status Colors ── */
  --status-online:   #2dd4bf;    /* match site's teal for success/online */
  --status-warning:  #f59e0b;    /* amber */
  --status-critical: #ef4444;    /* red */
  --status-offline:  #475569;    /* slate-600 */

  /* ── Card Styling (exact from site) ── */
  --card-bg:      rgba(10, 18, 32, 0.70);
  --card-border:  0.667px solid rgb(45, 212, 191);
  --card-radius:  12px;
  --card-shadow:  0 0 20px rgba(45, 212, 191, 0.05);
}
```

**Google Fonts to import** (exact fonts the site uses):
```html
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

**Tailwind config** — extend with all CSS variables above plus:
```js
theme: {
  extend: {
    colors: {
      'n10-teal':    '#2dd4bf',
      'n10-teal-hover': '#14b8a6',
      'n10-black':   '#000000',
      'n10-surface': '#050a12',
      'n10-card':    'rgba(10,18,32,0.7)',
      'n10-text':    'rgb(148,163,184)',
      'n10-heading': 'rgb(224,247,250)',
    },
    fontFamily: {
      heading: ['Space Grotesk', 'sans-serif'],
      body:    ['Inter', 'system-ui', 'sans-serif'],
      mono:    ['JetBrains Mono', 'monospace'],
    }
  }
}
```

**Visual style rules — match the website exactly:**

- **Page backgrounds**: alternate between `#000000` and `#050a12` per section,
  exactly as the Numbers10 website does (black → dark navy → black → dark navy)
- **Headings (h1–h3)**: `Space Grotesk` bold, color `rgb(224,247,250)` — the
  site's large hero text uses 700 weight at 72px
- **Body text**: `Inter`, color `rgb(148,163,184)` — slate-400 tone
- **Muted text / labels**: `rgb(100,116,139)` — slate-500, footer and meta text
- **Accent/teal text**: `#2dd4bf` — taglines, teal headings, icon colors, active states
- **Cards**: `rgba(10,18,32,0.7)` background, `0.667px solid rgb(45,212,191)`
  border, `12px` border radius — exactly matching the service cards on the site
- **Stat/metric numbers**: `Space Grotesk` bold `rgb(224,247,250)` large size —
  matching "38+", "4hr", "99.9%" style. Labels below in `Inter` uppercase
  `letter-spacing: 0.15em` `rgb(100,116,139)`
- **Section label pills** ("SERVICES", "ALERTS", "MACHINES"): thin border
  `rgba(45,212,191,0.4)`, `#050a12` bg, `#2dd4bf` text, `Inter` small-caps,
  `letter-spacing: 0.15em`, `6px 14px` padding, `6px` radius
- **Primary CTA button**: `#2dd4bf` background, `#000000` text, `8px` radius,
  bold `Inter` — "Get in Touch →" arrow style
- **Outline/secondary button**: transparent, `1px solid #2dd4bf` border,
  `#2dd4bf` text, `8px` radius — "Explore" secondary style
- **Navbar/header**: `rgba(0,0,0,0.88)` background, `backdrop-filter: blur(12px)`,
  `0.667px solid rgba(45,212,191,0.15)` bottom border — frosted glass like the site
- **Nav links**: `Inter` 400 weight 16px, `rgb(148,163,184)`, hover → `#2dd4bf`
- **Active sidebar item**: `3px solid #2dd4bf` left border + `rgba(45,212,191,0.08)` bg
- **Icon boxes**: `rgba(45,212,191,0.08)` bg, `rgba(45,212,191,0.15)` border,
  `8px` radius, `#2dd4bf` icon — exactly the service card icon squares on the site
- **Input fields**: `rgb(5,10,18)` bg, `0.667px solid rgba(45,212,191,0.15)` border,
  `rgb(224,247,250)` text, `8px` radius, focus ring `1px solid #2dd4bf`
- **Charts**: `#2dd4bf` stroke, `rgba(45,212,191,0.15)` area fill gradient
- **Gauge arcs**: `#2dd4bf` → `#14b8a6` gradient stroke
- **Online pulse dot**: `#2dd4bf` with CSS keyframe pulse animation
- **Offline dot**: `rgb(71,85,105)` static — slate-600
- **Footer**: `#000000` bg, `rgb(100,116,139)` text, logo + teal tagline left,
  quick links center, contact right — three-column exactly like the site footer
- **Table rows**: hover `rgba(45,212,191,0.05)`, border `rgba(45,212,191,0.1)`
- **Scrollbar**: 4px wide, `#2dd4bf` thumb, `#050a12` track
- **Dividers**: `rgba(45,212,191,0.15)` short centered line — like site's
  section subheading underlines
- **All metric numbers** (CPU %, RAM, bytes, temps): `JetBrains Mono` font
- **Blockquote/callout**: left border `3px solid #2dd4bf`, `rgba(10,18,32,0.7)` bg,
  italic `Inter` — matching the site's "We don't just fix IT problems" quote card

### Pages

#### `/login`
- Full-screen `#000000` background with radial teal glow at top:
  `radial-gradient(ellipse at 50% 0%, rgba(45,212,191,0.06) 0%, #000 60%)`
- Centered card: `rgba(10,18,32,0.7)` bg, `0.667px solid rgba(45,212,191,0.3)` border,
  `12px` radius, subtle `box-shadow: 0 0 40px rgba(45,212,191,0.08)`
- `logo.png` centered at top of card (~200px wide)
- "TECHNOLOGY SOLUTIONS" in `#2dd4bf`, `Inter`, `letter-spacing: 0.2em`, small-caps
- Email + password fields: `rgb(5,10,18)` bg, `0.667px solid rgba(45,212,191,0.15)`
  border, `rgb(224,247,250)` text, `8px` radius, `#2dd4bf` focus ring
- Sign In button: full-width, `#2dd4bf` bg, `#000` text, bold `Inter`, `8px` radius,
  hover glow `box-shadow: 0 0 20px rgba(45,212,191,0.4)`
- JWT stored in localStorage
- Auto-redirect if already authenticated

#### `/dashboard` (main view)
- **Top bar**: total machines, online count, active alerts badge, last refresh time
- **Machine Grid**: responsive card grid, each card shows:
  - Hostname + OS icon
  - Online/Offline status dot (green/red, pulsing if online)
  - CPU % gauge (arc gauge component)
  - RAM % gauge
  - Disk % bar
  - Last seen timestamp
  - Alert count badge (red if unacknowledged alerts)
  - Click → navigate to MachineDetail
- **Sidebar alerts panel**: collapsible, shows latest 5 unresolved alerts

#### `/machines/:id` (MachineDetail)
Full single-machine page with tabs:

**Tab: Overview**
- Machine info header: hostname, IP, OS, CPU model, uptime, last seen
- 4 large metric cards: CPU %, RAM %, Disk %, Network I/O
- 4 live time-series charts (last 1h, 6h, 24h, 7d selectable):
  - CPU usage over time
  - RAM usage over time
  - Disk I/O over time
  - Network bandwidth over time

**Tab: Processes**
- Table: top 20 processes sorted by CPU or RAM
- Columns: PID, Name, CPU%, RAM (MB), Status
- Toggle sort between CPU and RAM with column header click

**Tab: Services**
- Table of all Windows Services
- Status badges (Running=green, Stopped=red, etc.)
- Read-only view — status information only

**Tab: Software**
- Searchable table of all installed software
- Columns: Name, Version, Publisher, Install Date

**Tab: Event Logs**
- Table: Level (Error/Warning icon), Source, Event ID, Message, Time
- Filter by level and source

**Tab: Security**
- Cards: Firewall ON/OFF, AV status, Pending Windows Updates count, Last Boot

#### `/alerts`
Two sub-sections:

**Alert Rules**
- Table of all configured rules
- Columns: Name, Machine (or "All"), Metric, Condition, Threshold, Severity, Enabled toggle, Edit, Delete
- "+ New Rule" button opens modal form:
  - Rule name
  - Apply to: All machines / Specific machine dropdown
  - Metric: CPU % / RAM % / Disk % / CPU Temp / Net Latency / Service Down / etc.
  - Operator: > / < / =
  - Threshold value
  - Duration (seconds) before triggering
  - Severity: Info / Warning / Critical
  - Notify via: ☐ Email  ☐ Telegram

**Alert Events**
- Timeline/feed of alert events
- Filter by: Machine, Severity, Date range, Acknowledged/Unresolved
- Each event shows: Machine name, metric, value, threshold, time triggered, resolve time
- Acknowledge button per event
- Summary stats: total today, critical today, resolved today

#### `/reports`
- Select machine + date range
- Preview summary stats
- Download CSV button (metrics export)
- Download CSV button (alert events export)

#### `/settings`
- Admin profile: change password
- SMTP config: host, port, user, password, from address, test button
- Telegram config: bot token, chat ID, test button
- Data retention: set days (default 90)
- Alert engine interval: set seconds (default 30)

### Key Components

#### `MachineCard.jsx`
- Pulsing `--status-online` dot when online, static `--status-offline` when offline
- Mini sparkline (Recharts `<Sparkline>`) for CPU last 10 data points
- CPU and RAM arc gauges using SVG paths with `--gradient-logo` colors

#### `MetricGauge.jsx`
- SVG arc gauge that animates on value change
- Color transitions: `--status-online` (0–60%) → `--status-warning` (60–80%) → `--status-critical` (80–100%)
- Shows percentage in center in `JetBrains Mono`

#### `LiveChart.jsx`
- Recharts `<AreaChart>` with `--accent-primary` stroke and 20% opacity fill
- Time range selector buttons: 1H / 6H / 24H / 7D
- Tooltip showing exact value + timestamp
- Smooth curve interpolation

#### `AlertBadge.jsx`
- `--status-critical` pulsing badge with count of unresolved critical alerts
- Auto-updates every 30 seconds

#### `Sidebar.jsx`
- Top section: `logo.png` full-size when expanded (~160px wide), cropped to just
  the diamond icon (~36px) when sidebar is collapsed
- Navigation items: icon + label, `--accent-primary` 3px left border + `--bg-elevated`
  background when active, fade transition on hover
- Bottom: logged-in admin username + logout icon button
- Collapsible with smooth width transition (240px ↔ 60px)

#### `Navbar.jsx`
- Top bar with page title on left
- Right side: unresolved alert badge, last refresh timestamp, admin avatar/initials

### Real-time Updates
- `useMetrics` hook polls `/api/metrics/{id}/latest` every **30 seconds**
- `useAlerts` hook polls `/api/alerts/events/unresolved` every **60 seconds**
- Optional: WebSocket endpoint `WS /ws/metrics/{machine_id}` for live push
  (implement if time permits, fallback to polling otherwise)

---

## 🐳 Deployment — Docker Compose

### ⚠️ Port Assignments — Do NOT use these already-occupied ports:
```
OCCUPIED (do not use): 22, 80, 443, 8080, 8081
```

### ✅ Use these ports instead:
```
Nginx reverse proxy  →  8443  (HTTPS, public-facing entry point for dashboard)
FastAPI backend      →  8888  (internal only, proxied by nginx)
React frontend       →  3030  (internal only, proxied by nginx)
PostgreSQL           →  5433  (internal only, non-default for security)
```

The `setup.sh` script must also run:
```bash
sudo ufw allow 8443/tcp   # open only this one port for the dashboard
```

Generate a complete `docker-compose.yml`:

```yaml
services:

  db:
    image: timescale/timescaledb:latest-pg16
    ports:
      - "127.0.0.1:5433:5432"   # bind to localhost only — never expose DB publicly
    environment:
      POSTGRES_DB: pcmonitor
      POSTGRES_USER: pcmonitor
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "127.0.0.1:8888:8888"   # internal only
    environment:
      DATABASE_URL: postgresql+asyncpg://pcmonitor:${DB_PASSWORD}@db:5432/pcmonitor
      SECRET_KEY: ${SECRET_KEY}
      SMTP_HOST: ${SMTP_HOST}
      TELEGRAM_TOKEN: ${TELEGRAM_TOKEN}
    depends_on: [db]
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "127.0.0.1:3030:80"     # internal only
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "8443:8443"              # ← ONLY public-facing port
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro   # SSL certs (Let's Encrypt or self-signed)
    depends_on: [backend, frontend]
    restart: unless-stopped

volumes:
  pgdata:
```

Generate a complete `Dockerfile` for the backend (FastAPI on port 8888).
Generate a complete `Dockerfile` for the frontend (Vite build served by nginx on port 80 internally).

### `nginx.conf` rules:
- Listen on `8443` (HTTPS with SSL)
- `location /api/` → proxy to `http://backend:8888`
- `location /ws/` → proxy to `http://backend:8888` with WebSocket upgrade headers
- `location /` → proxy to `http://frontend:80`
- GZIP compression enabled
- Security headers: `X-Frame-Options`, `X-Content-Type-Options`, `HSTS`

Generate:
- `.env.example` with all required environment variables documented
- `nginx.conf` with the above rules
- `setup.sh` — one-command VPS setup script:
  ```bash
  # 1. Install Docker + Docker Compose
  # 2. Clone repo
  # 3. Copy .env.example → .env and prompt for passwords
  # 4. Generate self-signed SSL cert into ./certs/ if none exists
  # 5. Run: docker compose up -d --build
  # 6. Open UFW port 8443
  # 7. Print: "Dashboard running at https://YOUR-IP:8443"
  ```

---

## 🔒 Security Requirements

- **The system is strictly read-only / monitoring-only** — the backend never
  sends commands, scripts, or instructions back to any probe. Data flows in
  one direction only: probe → backend. There is no remote command, remote
  shell, reboot, shutdown, or script execution capability anywhere in the system.
- All probe → backend communication uses a **per-machine API key** (256-bit random,
  stored hashed in DB, sent as `X-API-Key` header)
- Admin dashboard uses **JWT** (15-min access token + 7-day refresh token)
- API keys are **never** returned in API responses after creation — shown once
  at registration time only, then only the hash is stored
- Rate limit the metrics ingest endpoint: max 10 req/min per API key
- All passwords hashed with **bcrypt** (cost factor 12)
- CORS configured to allow only the admin dashboard origin
- Backend validates all incoming metric data with Pydantic strict min/max ranges
- PostgreSQL bound to `127.0.0.1` only — never exposed publicly
- Backend bound to `127.0.0.1:8888` — only reachable via nginx, never directly
- Only port **8443** is exposed publicly via UFW

---

## 🏢 Multi-Company / Multi-Tenant Architecture

This is critical. Joe manages IT for **multiple separate client companies**.
Each company's PCs must be isolated from other companies in the dashboard.

### Database — `companies` table
```
id, name, slug (unique), contact_name, contact_email,
notes, created_at, is_active
```

### Updated `machines` table — add company FK
```
id, company_id (FK → companies), hostname, display_name,
api_key_hash, os_version, cpu_model, total_ram_gb,
ip_address, mac_address, last_seen, is_online,
registered_at, group_tag, notes
```

### Updated `alert_rules` — add company scope
```
id, company_id (nullable = global rule), machine_id (nullable),
name, metric_field, operator, threshold, duration_seconds,
severity, enabled, notify_email, notify_telegram
```

### Probe — Company-Aware Registration

The `config.ini` must include a `company_token` field:
```ini
[server]
url = https://your-vps.com:8443
company_token = COMPANY_SPECIFIC_TOKEN_HERE
ingest_interval_seconds = 30

[hardware]
use_open_hardware_monitor = false
```

**How it works:**
- Each client company gets a **unique company token** generated in the dashboard
- The probe sends this `company_token` in the `POST /api/machines/register` request
- The backend looks up which company this token belongs to and assigns the machine
  to that company automatically
- The probe does NOT need to know the company name — only the token
- Different client companies have completely separate tokens
- If a token is invalid, registration is rejected with 401

### New API Endpoints for Companies

```
GET  /api/companies                    — list all companies
POST /api/companies                    — create new company
GET  /api/companies/{id}               — company detail + machine count
PATCH /api/companies/{id}              — update name, contact, notes
DELETE /api/companies/{id}             — soft delete (set is_active=False)
GET  /api/companies/{id}/token         — get/regenerate company registration token
GET  /api/companies/{id}/machines      — list machines for this company
GET  /api/companies/{id}/alerts        — active alerts for this company
```

### Frontend — Company-Aware Dashboard

#### New page: `/companies`
- Grid of company cards, each showing:
  - Company name + slug
  - Number of machines online / total
  - Active alert count badge
  - Last activity timestamp
  - Click → filters dashboard to that company only
- "**+ Add Company**" button — modal form: name, contact name, contact email, notes
- Each company card has a "**Copy Token**" button to copy the registration token
  (this is what you paste into `config.ini` for that company's probes)
- "**Regenerate Token**" button per company (invalidates old token, all existing
  machines of that company remain — only new registrations are affected)

#### Updated `/dashboard`
- Add **company filter dropdown** at top: "All Companies" (default) or select one
- Machine cards show a **company badge/tag** in the corner
- Stats bar shows counts per selected company or totals if "All" selected

#### Updated `/machines/:id`
- Machine detail header shows which company this machine belongs to
- Breadcrumb: Companies → Company Name → Machine Name

#### Updated `/alerts`
- Alert rules and events have a **company column**
- Can filter alert view by company
- Alert rules can be scoped to: All Companies / Specific Company / Specific Machine

#### Updated `/settings`
- Admin can set a **default alert email per company** (overrides global SMTP from)
- Can configure **per-company Telegram chat ID** for alerts

### Probe Installer — Multi-Company Workflow

When building the `.exe` for a specific client company:

1. Admin goes to `/companies/{id}` in the dashboard
2. Clicks "**Copy Company Token**"
3. The `config.ini` template is pre-filled with:
   - Server URL
   - That company's unique token
4. Admin drops `PCMonitorProbe_Setup.exe` + `config.ini` onto the client's PC
5. Runs the exe — probe installs as Windows Service, registers with the backend,
   machine appears automatically under the correct company in the dashboard

**Alternative — baked-in token build:**
The `build_exe.bat` script accepts an optional `COMPANY_TOKEN` argument so the
token can be compiled directly into the exe, meaning the client only needs to
run the single exe with no config file needed:
```bat
build_exe.bat COMPANY_TOKEN=abc123xyz
```
This embeds the token at build time so there's zero configuration required
on the client side — just run the exe and it works.

### Data Isolation Rules
- An admin can see ALL companies (Joe is the only admin)
- Machines from Company A never appear in Company B's view when filtered
- Alert rules scoped to Company A do not fire for Company B machines
- Deleting a company sets `is_active=False` — machines are hidden but data
  is retained for 90 days before the retention job purges it
- Company tokens are stored hashed in the DB — never retrievable in plain text
  after creation (same as machine API keys)

---

## 📦 Deliverables Checklist

Claude Code must produce all of the following, fully working and production-ready:

- [ ] `backend/` — complete FastAPI application, all routes, models, services
- [ ] `backend/app/models/company.py` — company + company token model
- [ ] `backend/app/api/companies.py` — company CRUD + token management
- [ ] `backend/alembic/` — initial migration that creates all tables including `companies`
- [ ] `backend/docker-compose.yml` + `backend/Dockerfile`
- [ ] `backend/.env.example`
- [ ] `probe/` — complete Python Windows Service, all collectors
- [ ] `probe/installer.py` — Windows Service installer/uninstaller
- [ ] `probe/build_exe.bat` — PyInstaller build script (supports optional `COMPANY_TOKEN=` arg)
- [ ] `probe/config.ini` — template config with `company_token` field
- [ ] `frontend/` — complete React app, all pages and components
- [ ] `frontend/src/pages/Companies.jsx` — company management page
- [ ] `frontend/package.json` + `tailwind.config.js` + `vite.config.js`
- [ ] `nginx.conf` — production reverse proxy on port **8443**
- [ ] `setup.sh` — one-command VPS deployment script (opens UFW 8443)
- [ ] `README.md` — full setup guide:
  - VPS setup steps
  - Port assignments and UFW rules
  - How to deploy the backend
  - How to add a new client company in the dashboard
  - How to generate and copy a company token
  - How to install the probe on a Windows PC (with config.ini)
  - How to build a baked-in token probe EXE for a specific company
  - Default admin credentials and how to change them
  - Environment variable reference

---

## 🚀 Build Instructions for Claude Code

1. **Start with the backend** — build models (`company` first, then `machine` with
   `company_id` FK, then `metric`, `alert`, `event_log`), then schemas, then API
   routes, then services. Run `alembic revision --autogenerate` to create the migration.

2. **Build the probe next** — start with `probe_agent.py` Windows Service skeleton,
   then add each collector one by one, then the installer. Ensure `config.ini`
   includes the `company_token` field and the registration endpoint sends it.

3. **Build the frontend last** — start with Vite scaffold + Tailwind config using
   the Numbers10 color palette, then routing + layout, then pages in this order:
   Login → Companies → Dashboard → MachineDetail → Alerts → Reports → Settings.

4. **Wire everything together** — ensure API base URLs point to port `8443`,
   CORS settings match, Docker Compose internal service names align, and the
   company token flow works end-to-end (create company → copy token → probe
   registers → machine appears under that company).

5. **Validate** — ensure: (a) probe can register under a company, (b) metrics
   ingest works, (c) the dashboard company filter isolates machines correctly,
   (d) alerts fire and acknowledge correctly, (e) all ports match the assignment.

---

## 💡 Extra Intelligence Notes for Claude Code

- Use **async/await throughout** the FastAPI backend — no sync DB calls
- The `metrics` table will grow large — add DB indexes on:
  `(machine_id, collected_at DESC)` and `(company_id, collected_at DESC)`
- Probe should **batch** missed metrics if it loses connectivity, sending a list
  of up to 10 snapshots on reconnect
- Machine `is_online` is determined server-side by the alert engine, not by the probe
- Alert deduplication: only create ONE `alert_event` per rule per machine per
  breach — do not create a new event every 30s while the breach is ongoing
- The frontend `MachineDetail` chart should **downsample** data for 7-day view
  (return 1 point per 15 minutes from backend instead of one per 30 seconds)
- Log all probe errors to `probe_errors.log` with rotation (max 5MB, 3 backups)
- If `OpenHardwareMonitor` is not running, hardware sensor collectors should
  gracefully return `null` for temperature fields — never crash the probe
- Probe should **verify SSL certificate** in production, with a config option
  `verify_ssl = false` for self-signed certs in dev environments
- **Company tokens** are long-lived (don't expire) but can be regenerated by the
  admin at any time — existing machines remain registered, only new registrations
  use the new token
- The `build_exe.bat` script should accept `COMPANY_TOKEN=xxx` as a command-line
  argument and use PyInstaller's `--add-data` or a constants file to embed the
  token, so the final `.exe` requires zero configuration from the client
- **Port summary for README:**
  ```
  Public:   8443  → nginx (HTTPS dashboard + API entry point)
  Internal: 8888  → FastAPI backend
  Internal: 3030  → React frontend (served by nginx container)
  Internal: 5433  → PostgreSQL (localhost only, never public)
  ```

---

*Build Numbers10 PCMonitor. Multi-company, production-ready, clean, and complete.*
