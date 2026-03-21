/// IPC between the Windows Service (headless) and the Tray App (user session).
/// The service writes a status snapshot to a JSON file every 30 seconds.
/// The tray app reads it to update the icon and status window.
///
/// Why a file? Service runs in Session 0 (isolated). Tray runs in user session.
/// A file in %ProgramData% is accessible from both.

use crate::config::status_path;
use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProbeStatus {
    /// True if last POST to backend succeeded
    pub connected: bool,
    pub server_url: String,
    pub company_token_hint: String, // first 8 chars only, for display
    pub machine_id: Option<String>,
    pub latency_ms: Option<u64>,
    pub last_metric_sent: Option<DateTime<Utc>>,
    pub service_version: String,
    pub cpu_percent: f32,
    pub ram_percent: f32,
    pub disk_percent: f32,
    pub error_message: Option<String>,
}

pub fn write_status(status: &ProbeStatus) -> Result<()> {
    let dir = crate::config::config_dir();
    std::fs::create_dir_all(&dir)?;
    let json = serde_json::to_string_pretty(status)?;
    std::fs::write(status_path(), json)?;
    Ok(())
}

pub fn read_status() -> Option<ProbeStatus> {
    let path = status_path();
    let raw = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&raw).ok()
}
