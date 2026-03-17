# Changelog

All notable changes to Numbers10 PCMonitor Pro are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]
> Changes staged for the next release

---

## [1.0.0] — Initial Release

### Added
#### Backend
- FastAPI async REST API (Python 3.10+)
- PostgreSQL 16 + TimescaleDB for time-series metric storage
- SQLAlchemy 2.x async ORM with Alembic migrations
- Multi-company architecture — `companies` table with unique registration tokens
- Machine auto-registration via company token (`POST /api/machines/register`)
- Per-machine API key authentication (256-bit, stored hashed)
- JWT admin authentication (15-min access + 7-day refresh tokens)
- Metrics ingestion endpoint with Pydantic validation
- Historical metrics query with downsampling for 7-day views
- Alert rules engine (APScheduler, 30-second evaluation cycle)
- Alert deduplication — one active event per rule per machine
- Alert auto-resolution when metric drops below threshold
- Email notifications via aiosmtplib (HTML formatted)
- Telegram bot notifications via httpx
- Data retention background job (configurable, default 90 days)
- Windows Services status collector
- Software inventory collector (Windows Registry)
- Windows Event Log collector (Error + Warning)
- Security status collector (Firewall, AV, Windows Update)
- Reports export — CSV for metrics and alert events
- Rate limiting on metrics ingest (10 req/min per API key)

#### Probe Agent
- Python Windows Service (`pywin32`) — auto-starts on boot
- CPU collector: usage per-core, frequency, temperature (WMI/OpenHardwareMonitor)
- Memory collector: RAM + swap usage
- Disk collector: all drives, usage, SMART health, I/O counters
- Network collector: per-interface bandwidth, latency ping, active connections
- Process collector: top 20 by CPU and RAM
- Windows Services collector (every 5 minutes)
- Windows Event Log collector (new Error/Warning events only)
- Hardware sensor collector: GPU (NVIDIA via pynvml), fan speeds
- Software inventory collector (every 24 hours)
- Security status collector: Firewall, Defender, Windows Update
- Offline metric batching — sends up to 10 missed snapshots on reconnect
- SSL certificate verification (configurable for self-signed certs)
- Rotating log file (5MB max, 3 backups)
- Company token baked into EXE via `build_exe.bat COMPANY_TOKEN=xxx`
- PyInstaller single-file EXE build with no runtime dependencies

#### Frontend
- React 18 + Vite + TailwindCSS
- Numbers10 brand theme: Space Grotesk headings, Inter body, JetBrains Mono metrics
- Exact color palette from www.numbers10.co.za (`#2dd4bf` teal, `#000000`/`#050a12` backgrounds)
- Frosted glass navbar (`backdrop-filter: blur(12px)`)
- Login page with Numbers10 logo and teal radial glow
- Companies page — grid of company cards with token management
- Dashboard — machine grid with company filter, live status, CPU/RAM gauges
- Machine Detail — 6 tabs: Overview, Processes, Services, Software, Event Logs, Security
- Live time-series charts (1H / 6H / 24H / 7D) with Recharts AreaChart
- Animated SVG arc gauges for CPU and RAM
- Alert Rules — create/edit/delete with full threshold configuration
- Alert Events — timeline feed with acknowledge, filter by company/severity/date
- Reports page — CSV export for metrics and alerts
- Settings — SMTP config, Telegram config, retention, admin profile
- Collapsible sidebar (240px ↔ 60px) with logo diamond icon when collapsed
- React Query for data fetching + caching
- Zustand for global state
- JWT auto-refresh on 401

#### Infrastructure
- Docker Compose with 4 services: db, backend, frontend, nginx
- Nginx reverse proxy on port **8443** (no conflict with 22/80/443/8080/8081)
- PostgreSQL on internal port 5433 (localhost only)
- FastAPI on internal port 8888
- React on internal port 3030
- `setup.sh` one-command VPS deployment with UFW rule for 8443
- Self-signed SSL cert generation if no cert present
- `.env.example` with all required variables documented

---

[Unreleased]: https://github.com/Joevikingroux/monitorpro/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Joevikingroux/monitorpro/releases/tag/v1.0.0
