/// Windows-specific collectors — services, software, event logs, security.
/// Services and security use WMI directly (no PowerShell subprocess overhead).
/// Event logs use PowerShell Get-WinEvent which is well-optimised for time filters.
/// All functions are synchronous blocking — call inside tokio::task::spawn_blocking.

use chrono::{DateTime, FixedOffset, NaiveDateTime, TimeZone, Utc};
use log::{info, warn};
use serde::{Deserialize, Serialize};
use std::process::Command;
use wmi::{COMLibrary, WMIConnection};

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
    pub installed_updates: Option<u32>,
}

// ── WMI helper ─────────────────────────────────────────────────────────────

fn wmi_connect(namespace: &str) -> Option<WMIConnection> {
    let com = match COMLibrary::without_security() {
        Ok(c) => c,
        Err(e) => {
            warn!("COM init for {}: {}", namespace, e);
            return None;
        }
    };
    match WMIConnection::with_namespace_path(namespace, com.into()) {
        Ok(w) => Some(w),
        Err(e) => {
            warn!("WMI connect to {} failed: {}", namespace, e);
            None
        }
    }
}

// ── PowerShell helper (kept for event logs only) ───────────────────────────

fn run_ps(script: &str) -> Option<String> {
    let result = Command::new("powershell.exe")
        .args([
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ])
        .output();

    match result {
        Err(e) => {
            warn!("PowerShell launch failed: {}", e);
            None
        }
        Ok(out) => {
            let stderr = String::from_utf8_lossy(&out.stderr);
            if !stderr.trim().is_empty() {
                warn!("PowerShell stderr: {}", stderr.trim());
            }
            let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if s.is_empty() { None } else { Some(s) }
        }
    }
}

// ── Services (WMI Win32_Service — instant, no subprocess) ─────────────────

pub fn collect_services() -> Vec<ServiceInfo> {
    #[derive(Deserialize)]
    #[allow(non_snake_case)]
    struct WmiService {
        Name: String,
        DisplayName: String,
        State: String,
        StartMode: String,
    }

    let wmi = match wmi_connect("ROOT\\CIMV2") {
        Some(w) => w,
        None => return vec![],
    };

    let results: Vec<WmiService> = match wmi.raw_query(
        "SELECT Name, DisplayName, State, StartMode FROM Win32_Service",
    ) {
        Ok(r) => r,
        Err(e) => {
            warn!("Win32_Service query failed: {}", e);
            return vec![];
        }
    };

    // Only send services that are worth seeing:
    //   • Currently Running (any startup type)
    //   • Auto-start but Stopped — these are broken/failed services
    // Skip Disabled+Stopped — there are 100+ on any Windows PC, all noise.
    let out: Vec<ServiceInfo> = results
        .into_iter()
        .filter(|s| {
            let running = s.State.eq_ignore_ascii_case("Running");
            let auto_stopped = s.StartMode.eq_ignore_ascii_case("Auto")
                && s.State.eq_ignore_ascii_case("Stopped");
            running || auto_stopped
        })
        .map(|s| ServiceInfo {
            service_name: s.Name,
            display_name: s.DisplayName,
            status: s.State,
            startup_type: s.StartMode,
        })
        .collect();

    info!("collect_services: {} relevant services via WMI", out.len());
    out
}

// ── Software inventory (registry — fast, no WMI Win32_Product) ────────────

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

            // Must have a display name
            let name: String = sub.get_value("DisplayName").unwrap_or_default();
            if name.is_empty() {
                continue;
            }

            // Must have an UninstallString — this is exactly what "Programs and Features"
            // uses to decide if something is a real user-installed app.
            let uninstall: String = sub.get_value("UninstallString").unwrap_or_default();
            if uninstall.is_empty() {
                continue;
            }

            // Skip system components flagged in the registry
            let system_component: u32 = sub.get_value("SystemComponent").unwrap_or(0);
            if system_component == 1 {
                continue;
            }

            // Skip Windows hotfixes / patches (KB articles)
            if sub_name.starts_with("KB") || name.starts_with("Update for") || name.starts_with("Hotfix") {
                continue;
            }

            // Skip common low-value Microsoft runtime redistributables
            let noise_prefixes = [
                "Microsoft Visual C++",
                "Microsoft .NET",
                "Microsoft Edge WebView2",
                "Windows Software Development Kit",
                "Windows Driver Kit",
            ];
            if noise_prefixes.iter().any(|p| name.starts_with(p)) {
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

    items.sort_by(|a, b| a.name.cmp(&b.name));
    items.dedup_by(|a, b| a.name == b.name);
    info!("collect_software: {} user-installed apps via registry", items.len());
    items
}

// ── Event logs (PowerShell Get-WinEvent — best for time-filtered queries) ──

pub fn collect_event_logs(_since_minutes: u64) -> Vec<EventLogEntry> {
    // Fetch the last 20 Error/Warning events from System and Application logs
    // regardless of time — this ensures we always have events to show, not just
    // events from the last 5-minute window which may well be empty on a healthy PC.
    let ps = r#"
        $results = @()
        foreach ($log in @('System','Application')) {
            $results += Get-WinEvent -FilterHashtable @{
                LogName = $log
                Level   = 1,2
            } -MaxEvents 20 -ErrorAction SilentlyContinue
        }
        if ($results.Count -eq 0) { exit 0 }
        $results | Sort-Object TimeCreated -Descending | Select-Object -First 20 |
        Select-Object `
            @{N='log_source';   E={$_.ProviderName}},
            @{N='event_id';     E={[int]$_.Id}},
            @{N='level';        E={$_.LevelDisplayName}},
            @{N='message';      E={($_.Message -replace '\r\n',' ' -replace '\n',' ').Substring(0,[Math]::Min(500,$_.Message.Length))}},
            @{N='occurred_at';  E={$_.TimeCreated.ToUniversalTime().ToString('o')}} |
        ConvertTo-Json -Compress -Depth 2
    "#;

    let raw = match run_ps(&ps) {
        Some(r) => r,
        None => {
            info!("collect_event_logs: no Error/Warning events found");
            return vec![];
        }
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

    let items: Vec<Ps> = match serde_json::from_str(&json) {
        Ok(v) => v,
        Err(e) => {
            warn!("collect_event_logs: JSON parse error: {}", e);
            vec![]
        }
    };
    let result: Vec<EventLogEntry> = items
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
        .collect();
    info!("collect_event_logs: {} entries", result.len());
    result
}

// ── Security info (registry for firewall, WMI for AV + boot time) ──────────

pub fn collect_security() -> SecurityInfo {
    // Firewall: read registry directly — instant, same method as Python probe
    let firewall_enabled = firewall_from_registry();

    // AV: WMI SecurityCenter2 — in-process, no subprocess
    let av_status = av_from_wmi();

    // Boot time: WMI Win32_OperatingSystem — in-process, no subprocess
    let last_boot_time = boot_time_from_wmi();

    // Installed Windows updates/hotfixes count via Win32_QuickFixEngineering
    let installed_updates = installed_updates_from_wmi();

    info!(
        "collect_security: firewall={:?} av={:?} last_boot={:?} updates={:?}",
        firewall_enabled, av_status, last_boot_time, installed_updates
    );
    SecurityInfo { firewall_enabled, av_status, last_boot_time, installed_updates }
}

fn firewall_from_registry() -> Option<bool> {
    use winreg::{enums::{HKEY_LOCAL_MACHINE, KEY_READ}, RegKey};
    let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);
    // Check all three profiles — if any is enabled, firewall is on
    let profiles = [
        r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile",
        r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\PublicProfile",
        r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\DomainProfile",
    ];
    for profile in &profiles {
        if let Ok(key) = hklm.open_subkey_with_flags(profile, KEY_READ) {
            let val: u32 = key.get_value("EnableFirewall").unwrap_or(0);
            if val != 0 {
                return Some(true);
            }
        }
    }
    Some(false)
}

fn av_from_wmi() -> Option<String> {
    #[derive(Deserialize)]
    #[allow(non_snake_case)]
    struct WmiAV {
        displayName: String,
    }

    let wmi = wmi_connect("ROOT\\SecurityCenter2")?;
    let results: Vec<WmiAV> = wmi
        .raw_query("SELECT displayName FROM AntiVirusProduct")
        .map_err(|e| warn!("AntiVirusProduct WMI query failed: {}", e))
        .ok()?;
    results.into_iter().next().map(|av| av.displayName)
}

fn boot_time_from_wmi() -> Option<DateTime<Utc>> {
    #[derive(Deserialize)]
    #[allow(non_snake_case)]
    struct WmiOS {
        LastBootUpTime: String,
    }

    let wmi = wmi_connect("ROOT\\CIMV2")?;
    let results: Vec<WmiOS> = wmi
        .raw_query("SELECT LastBootUpTime FROM Win32_OperatingSystem")
        .map_err(|e| warn!("Win32_OperatingSystem WMI query failed: {}", e))
        .ok()?;
    results.into_iter().next().and_then(|os| parse_wmi_datetime(&os.LastBootUpTime))
}

fn installed_updates_from_wmi() -> Option<u32> {
    #[derive(Deserialize)]
    #[allow(non_snake_case)]
    struct WmiHotfix {
        HotFixID: String,
    }

    let wmi = wmi_connect("ROOT\\CIMV2")?;
    // Select only HotFixID to minimise data transfer — we just need the count
    let results: Vec<WmiHotfix> = wmi
        .raw_query("SELECT HotFixID FROM Win32_QuickFixEngineering")
        .map_err(|e| warn!("Win32_QuickFixEngineering query failed: {}", e))
        .ok()?;
    Some(results.len() as u32)
}

/// Parse WMI DMTF datetime string: "yyyyMMddHHmmss.ffffff+UUU"
fn parse_wmi_datetime(s: &str) -> Option<DateTime<Utc>> {
    if s.len() < 25 {
        return None;
    }
    let naive = NaiveDateTime::parse_from_str(&s[..14], "%Y%m%d%H%M%S").ok()?;
    let sign = s.chars().nth(21)?;
    let offset_mins: i32 = s[22..25].parse().ok()?;
    let offset_secs = match sign {
        '+' => offset_mins * 60,
        '-' => -offset_mins * 60,
        _ => 0,
    };
    let tz = FixedOffset::east_opt(offset_secs)?;
    Some(tz.from_local_datetime(&naive).single()?.with_timezone(&Utc))
}
