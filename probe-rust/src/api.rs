use anyhow::{bail, Result};
use reqwest::{Client, ClientBuilder};
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};

use crate::config::ProbeConfig;
use crate::collectors::MetricSnapshot;
use crate::collectors::windows_ext::{ServiceInfo, SoftwareInfo, EventLogEntry};

// ── Request / Response types — must match backend schemas exactly ─────────

#[derive(Serialize)]
pub struct RegisterRequest {
    // backend MachineRegisterRequest field order
    pub hostname: String,
    pub os_version: String,
    pub cpu_model: String,
    pub total_ram_gb: f64,
    pub ip_address: String,
    pub mac_address: String,
    pub company_token: String,  // backend expects this in the JSON body
}

#[derive(Deserialize)]
pub struct RegisterResponse {
    // backend MachineRegisterResponse: machine_id is int, api_key is str
    pub machine_id: u32,
    pub api_key: String,
}

/// backend MetricBatchIngestRequest: { metrics: [...] }
#[derive(Serialize)]
pub struct BatchIngestRequest {
    pub metrics: Vec<MetricPayload>,
}

/// Matches backend MetricIngestRequest field names exactly.
/// Extra fields (per_core_percent, swap_*) are simply ignored by Pydantic.
#[derive(Serialize)]
pub struct MetricPayload {
    pub collected_at: chrono::DateTime<chrono::Utc>,
    pub cpu_percent: Option<f32>,
    pub cpu_freq_mhz: Option<f64>,   // backend expects float
    pub cpu_temp_c: Option<f32>,
    pub ram_percent: Option<f32>,
    pub ram_used_gb: Option<f64>,
    pub ram_total_gb: Option<f64>,
    pub disk_usage: Option<serde_json::Value>,
    pub net_sent_mb: Option<f64>,
    pub net_recv_mb: Option<f64>,
    pub net_latency_ms: Option<f64>, // backend expects float
    pub top_processes: Option<serde_json::Value>,
    pub gpu_percent: Option<f32>,
    pub gpu_temp_c: Option<f32>,
    pub gpu_vram_used_mb: Option<f64>,
    pub firewall_enabled: Option<bool>,
    pub av_status: Option<String>,
    pub last_boot_time: Option<chrono::DateTime<chrono::Utc>>,
    pub installed_updates: Option<u32>,
}

impl From<&MetricSnapshot> for MetricPayload {
    fn from(s: &MetricSnapshot) -> Self {
        Self {
            collected_at: s.collected_at,
            cpu_percent: Some(s.cpu_percent),
            cpu_freq_mhz: s.cpu_freq_mhz.map(|v| v as f64),
            cpu_temp_c: s.cpu_temp_c,
            ram_percent: Some(s.ram_percent),
            ram_used_gb: Some(s.ram_used_gb),
            ram_total_gb: Some(s.ram_total_gb),
            disk_usage: serde_json::to_value(&s.disk_usage).ok(),
            net_sent_mb: Some(s.net_sent_mb),
            net_recv_mb: Some(s.net_recv_mb),
            net_latency_ms: s.net_latency_ms.map(|v| v as f64),
            top_processes: serde_json::to_value(&s.top_processes).ok(),
            gpu_percent: s.gpu_percent,
            gpu_temp_c: s.gpu_temp_c,
            gpu_vram_used_mb: s.gpu_vram_used_mb,
            firewall_enabled: s.firewall_enabled,
            av_status: s.av_status.clone(),
            last_boot_time: s.last_boot_time,
            installed_updates: s.installed_updates,
        }
    }
}

// ── API client ────────────────────────────────────────────────────────────

pub struct ApiClient {
    client: Client,
    base_url: String,
    api_key: String,
}

impl ApiClient {
    pub fn new(cfg: &ProbeConfig, api_key: String) -> Result<Self> {
        let client = ClientBuilder::new()
            .timeout(Duration::from_secs(30))
            .danger_accept_invalid_certs(!cfg.verify_ssl)
            .build()?;

        Ok(Self {
            client,
            base_url: cfg.server_url.trim_end_matches('/').to_string(),
            api_key,
        })
    }

    /// POST batch to /api/metrics/ingest/batch — the correct batch endpoint.
    pub async fn ingest(&self, snapshots: Vec<MetricSnapshot>) -> Result<u64> {
        let url = format!("{}/api/metrics/ingest/batch", self.base_url);
        let payload = BatchIngestRequest {
            metrics: snapshots.iter().map(MetricPayload::from).collect(),
        };

        let t0 = Instant::now();
        let resp = self
            .client
            .post(&url)
            .header("X-API-Key", &self.api_key)
            .json(&payload)
            .send()
            .await?;
        let latency_ms = t0.elapsed().as_millis() as u64;

        if !resp.status().is_success() {
            let code = resp.status();
            let body = resp.text().await.unwrap_or_default();
            bail!("Ingest failed {}: {}", code, body);
        }

        Ok(latency_ms)
    }

    pub async fn post_services(&self, machine_id: &str, services: Vec<ServiceInfo>) -> Result<()> {
        let url = format!("{}/api/machines/{}/services", self.base_url, machine_id);
        let resp = self.client.post(&url)
            .header("X-API-Key", &self.api_key)
            .json(&services)
            .send().await?;
        if !resp.status().is_success() {
            bail!("post_services {} failed: {}", resp.status(), resp.text().await.unwrap_or_default());
        }
        Ok(())
    }

    pub async fn post_software(&self, machine_id: &str, software: Vec<SoftwareInfo>) -> Result<()> {
        let url = format!("{}/api/machines/{}/software", self.base_url, machine_id);
        let resp = self.client.post(&url)
            .header("X-API-Key", &self.api_key)
            .json(&software)
            .send().await?;
        if !resp.status().is_success() {
            bail!("post_software {} failed: {}", resp.status(), resp.text().await.unwrap_or_default());
        }
        Ok(())
    }

    pub async fn post_event_logs(&self, machine_id: &str, events: Vec<EventLogEntry>) -> Result<()> {
        if events.is_empty() { return Ok(()); }
        let url = format!("{}/api/machines/{}/event-logs", self.base_url, machine_id);
        let resp = self.client.post(&url)
            .header("X-API-Key", &self.api_key)
            .json(&events)
            .send().await?;
        if !resp.status().is_success() {
            bail!("post_event_logs {} failed: {}", resp.status(), resp.text().await.unwrap_or_default());
        }
        Ok(())
    }
}

/// One-shot registration — returns (api_key, machine_id_as_string).
pub async fn register(cfg: &ProbeConfig, info: RegisterRequest) -> Result<(String, String)> {
    let client = ClientBuilder::new()
        .timeout(Duration::from_secs(30))
        .danger_accept_invalid_certs(!cfg.verify_ssl)
        .build()?;

    let url = format!("{}/api/machines/register", cfg.server_url.trim_end_matches('/'));

    let resp = client
        .post(&url)
        .json(&info)   // company_token is in the body, no separate header needed
        .send()
        .await?;

    if !resp.status().is_success() {
        let code = resp.status();
        let body = resp.text().await.unwrap_or_default();
        bail!("Registration failed HTTP {}: {}", code, body);
    }

    let reg: RegisterResponse = resp.json().await
        .map_err(|e| anyhow::anyhow!("Failed to parse registration response: {}", e))?;

    Ok((reg.api_key, reg.machine_id.to_string()))
}
