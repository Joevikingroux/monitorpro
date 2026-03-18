/// Windows-specific collectors: services, software inventory, event logs, security.
/// All functions are synchronous blocking — call inside tokio::task::spawn_blocking.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::process::Command;

// ── Public structs (serialized and sent to backend) ────────────────────────

#[derive(Debug, Clone, Serialize)]
pub struct ServiceInfo {
    pub service_name: String,
    pub display_name: String,
    pub status: String,
    pub startup_type: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct SoftwareInfo {
    pub name: String,
    pub version: Option<String>,
    pub publisher: Option<String>,
    pub install_date: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct EventLogEntry {
    pub log_source: String,
    pub event_id: Option<u32>,
    pub level: String,
    pub message: String,
    pub occurred_at: String, // ISO 8601 UTC string
}

#[derive(Debug, Clone, Default)]
pub struct SecurityInfo {
    pub firewall_enabled: Option<bool>,
    pub av_status: Option<String>,
    pub last_boot_time: Option<DateTime<Utc>>,
}

// ── PowerShell helper ──────────────────────────────────────────────────────

fn run_ps(script: &str) -> Option<String> {
    let out = Command::new("powershell.exe")
        .args([
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ])
        .output()
        .ok()?;
    let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
    if s.is_empty() { None } else { Some(s) }
}

// ── Services ───────────────────────────────────────────────────────────────

pub fn collect_services() -> Vec<ServiceInfo> {
    let ps = r#"
        $svc = Get-Service -ErrorAction SilentlyContinue
        $svc | ForEach-Object {
            [PSCustomObject]@{
                service_name = $_.ServiceName
                display_name = $_.DisplayName
                status       = $_.Status.ToString()
                startup_type = try { $_.StartType.ToString() } catch { 'Unknown' }
            }
        } | ConvertTo-Json -Compress -Depth 2
    "#;

    let raw = match run_ps(ps) {
        Some(r) => r,
        None => return vec![],
    };

    // PowerShell returns a single object (not array) when there's only 1 service
    let json = if raw.trim_start().starts_with('[') {
        raw
    } else {
        format!("[{}]", raw)
    };

    #[derive(Deserialize)]
    struct Ps {
        service_name: String,
        display_name: String,
        status: String,
        startup_type: String,
    }

    let items: Vec<Ps> = serde_json::from_str(&json).unwrap_or_default();
    items
        .into_iter()
        .map(|s| ServiceInfo {
            service_name: s.service_name,
            display_name: s.display_name,
            status: s.status,
            startup_type: s.startup_type,
        })
        .collect()
}

// ── Software inventory (via registry — fast, no WMI Win32_Product) ─────────

pub fn collect_software() -> Vec<SoftwareInfo> {
    use winreg::{
        enums::{HKEY_LOCAL_MACHINE, KEY_READ},
        RegKey,
    };

    let mut items: Vec<SoftwareInfo> = Vec::new();
    let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);

    let paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ];

    for path in &paths {
        let Ok(key) = hklm.open_subkey_with_flags(path, KEY_READ) else {
            continue;
        };
        for sub_name in key.enum_keys().flatten() {
            let Ok(sub) = key.open_subkey_with_flags(&sub_name, KEY_READ) else {
                continue;
            };
            let name: String = sub.get_value("DisplayName").unwrap_or_default();
            if name.is_empty() {
                continue;
            }
            // Skip Windows system components
            let system_component: u32 = sub.get_value("SystemComponent").unwrap_or(0);
            if system_component == 1 {
                continue;
            }
            items.push(SoftwareInfo {
                name,
                version: sub.get_value("DisplayVersion").ok(),
                publisher: sub.get_value("Publisher").ok(),
                install_date: sub.get_value("InstallDate").ok(),
            });
        }
    }

    // Deduplicate by name
    items.sort_by(|a, b| a.name.cmp(&b.name));
    items.dedup_by(|a, b| a.name == b.name);
    items
}

// ── Event logs (last N minutes, Errors + Warnings only) ───────────────────

pub fn collect_event_logs(since_minutes: u64) -> Vec<EventLogEntry> {
    let ps = format!(
        r#"
        $since = (Get-Date).AddMinutes(-{})
        $results = @()
        foreach ($log in @('System','Application')) {{
            $results += Get-WinEvent -FilterHashtable @{{
                LogName   = $log
                Level     = 1,2
                StartTime = $since
            }} -MaxEvents 50 -ErrorAction SilentlyContinue
        }}
        if ($results.Count -eq 0) {{ exit 0 }}
        $results | Select-Object `
            @{{N='log_source';   E={{$_.ProviderName}}}},
            @{{N='event_id';     E={{[int]$_.Id}}}},
            @{{N='level';        E={{$_.LevelDisplayName}}}},
            @{{N='message';      E={{($_.Message -replace '\r\n',' ' -replace '\n',' ').Substring(0,[Math]::Min(500,$_.Message.Length))}}}},
            @{{N='occurred_at';  E={{$_.TimeCreated.ToUniversalTime().ToString('o')}}}} |
        ConvertTo-Json -Compress -Depth 2
        "#,
        since_minutes
    );

    let raw = match run_ps(&ps) {
        Some(r) => r,
        None => return vec![],
    };

    let json = if raw.trim_start().starts_with('[') {
        raw
    } else {
        format!("[{}]", raw)
    };

    #[derive(Deserialize)]
    struct Ps {
        log_source: Option<String>,
        event_id: Option<u32>,
        level: Option<String>,
        message: Option<String>,
        occurred_at: Option<String>,
    }

    let items: Vec<Ps> = serde_json::from_str(&json).unwrap_or_default();
    items
        .into_iter()
        .filter_map(|e| {
            Some(EventLogEntry {
                log_source: e.log_source.unwrap_or_default(),
                event_id: e.event_id,
                level: e.level.unwrap_or_else(|| "Error".into()),
                message: e.message.unwrap_or_default(),
                occurred_at: e.occurred_at?,
            })
        })
        .collect()
}

// ── Security info ──────────────────────────────────────────────────────────

pub fn collect_security() -> SecurityInfo {
    // Firewall — any profile enabled counts as "on"
    let firewall_enabled = run_ps(
        "if ((Get-NetFirewallProfile -ErrorAction SilentlyContinue | Where-Object Enabled -eq True).Count -gt 0) { 'true' } else { 'false' }"
    ).map(|s| s.trim().to_lowercase() == "true");

    // Antivirus via SecurityCenter2
    let av_status = run_ps(
        r#"try {
            $av = Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction Stop
            if ($av) { ($av | Select-Object -First 1).displayName } else { 'None detected' }
        } catch { 'Not available' }"#,
    );

    // Last boot time
    let last_boot_time = run_ps(
        "(Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction SilentlyContinue).LastBootUpTime.ToUniversalTime().ToString('o')"
    ).and_then(|s| s.trim().parse::<DateTime<Utc>>().ok());

    SecurityInfo {
        firewall_enabled,
        av_status,
        last_boot_time,
    }
}
