/// Config baked into the binary at compile time (set via build.bat env vars)
pub const BAKED_SERVER_URL: Option<&str> = option_env!("SERVER_URL");
pub const BAKED_COMPANY_TOKEN: Option<&str> = option_env!("COMPANY_TOKEN");

pub const DEFAULT_SERVER_URL: &str = "https://monitor.numbers10.co.za:8443";
pub const SERVICE_NAME: &str = "PCMonitorProbe";
pub const SERVICE_DISPLAY: &str = "Numbers10 PC Monitor Probe";
pub const SERVICE_DESC: &str =
    "Collects system metrics and sends to Numbers10 PCMonitor server";
pub const TRAY_TOOLTIP: &str = "Numbers10 PCMonitor";
pub const APP_VERSION: &str = env!("CARGO_PKG_VERSION");

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Runtime config — stored in %ProgramData%\Numbers10\PCMonitor\config.json
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProbeConfig {
    pub server_url: String,
    pub company_token: String,
    /// API key assigned by server after successful registration
    pub api_key: Option<String>,
    /// Machine ID assigned by server after registration
    pub machine_id: Option<String>,
    pub ingest_interval_secs: u64,
    pub verify_ssl: bool,
}

impl Default for ProbeConfig {
    fn default() -> Self {
        Self {
            server_url: BAKED_SERVER_URL
                .unwrap_or(DEFAULT_SERVER_URL)
                .to_string(),
            company_token: BAKED_COMPANY_TOKEN.unwrap_or("").to_string(),
            api_key: None,
            machine_id: None,
            ingest_interval_secs: 30,
            verify_ssl: true,
        }
    }
}

pub fn config_dir() -> PathBuf {
    // %ProgramData%\Numbers10\PCMonitor
    let base = std::env::var("ProgramData")
        .unwrap_or_else(|_| "C:\\ProgramData".to_string());
    PathBuf::from(base).join("Numbers10").join("PCMonitor")
}

pub fn config_path() -> PathBuf {
    config_dir().join("config.json")
}

pub fn log_path() -> PathBuf {
    config_dir().join("probe.log")
}

pub fn status_path() -> PathBuf {
    config_dir().join("status.json")
}

pub fn install_dir() -> PathBuf {
    let base = std::env::var("ProgramFiles")
        .unwrap_or_else(|_| "C:\\Program Files".to_string());
    PathBuf::from(base)
        .join("Numbers10")
        .join("PCMonitor")
}

pub fn load_config() -> Result<ProbeConfig> {
    let path = config_path();
    if !path.exists() {
        return Ok(ProbeConfig::default());
    }
    let raw = std::fs::read_to_string(&path)
        .with_context(|| format!("Reading config from {:?}", path))?;
    let cfg: ProbeConfig =
        serde_json::from_str(&raw).context("Parsing config.json")?;
    Ok(cfg)
}

pub fn save_config(cfg: &ProbeConfig) -> Result<()> {
    let dir = config_dir();
    std::fs::create_dir_all(&dir)?;
    let json = serde_json::to_string_pretty(cfg)?;
    std::fs::write(config_path(), json)?;
    Ok(())
}
