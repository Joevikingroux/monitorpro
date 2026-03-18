use anyhow::Result;
use log::{error, info, warn};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::time::{Duration, Instant};
use sysinfo::{CpuRefreshKind, MemoryRefreshKind, ProcessRefreshKind, RefreshKind, System};
use windows_service::{
    define_windows_service,
    service::{
        ServiceControl, ServiceControlAccept, ServiceExitCode, ServiceState, ServiceStatus,
        ServiceType,
    },
    service_control_handler::{self, ServiceControlHandlerResult},
    service_dispatcher,
};

use crate::{api, collectors, config, ipc};

define_windows_service!(ffi_service_main, service_main);

pub fn start() -> Result<()> {
    service_dispatcher::start(config::SERVICE_NAME, ffi_service_main)
        .map_err(|e| anyhow::anyhow!("Service dispatcher: {}", e))
}

fn service_main(args: Vec<std::ffi::OsString>) {
    if let Err(e) = run_service(args) {
        error!("Service error: {}", e);
    }
}

fn run_service(_args: Vec<std::ffi::OsString>) -> Result<()> {
    let running = Arc::new(AtomicBool::new(true));
    let r = running.clone();

    let status_handle = service_control_handler::register(
        config::SERVICE_NAME,
        move |ctrl| match ctrl {
            ServiceControl::Stop | ServiceControl::Shutdown => {
                r.store(false, Ordering::SeqCst);
                ServiceControlHandlerResult::NoError
            }
            ServiceControl::Interrogate => ServiceControlHandlerResult::NoError,
            _ => ServiceControlHandlerResult::NotImplemented,
        },
    )?;

    status_handle.set_service_status(ServiceStatus {
        service_type: ServiceType::OWN_PROCESS,
        current_state: ServiceState::Running,
        controls_accepted: ServiceControlAccept::STOP | ServiceControlAccept::SHUTDOWN,
        exit_code: ServiceExitCode::Win32(0),
        checkpoint: 0,
        wait_hint: Duration::default(),
        process_id: None,
    })?;

    info!("PCMonitor Probe v{} started", config::APP_VERSION);

    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(metric_loop(running))?;

    status_handle.set_service_status(ServiceStatus {
        service_type: ServiceType::OWN_PROCESS,
        current_state: ServiceState::Stopped,
        controls_accepted: ServiceControlAccept::empty(),
        exit_code: ServiceExitCode::Win32(0),
        checkpoint: 0,
        wait_hint: Duration::default(),
        process_id: None,
    })?;

    info!("PCMonitor Probe stopped");
    Ok(())
}

async fn metric_loop(running: Arc<AtomicBool>) -> Result<()> {
    let mut cfg = config::load_config()?;

    // sysinfo System — refresh CPU + memory + processes each cycle
    let refresh_kind = RefreshKind::new()
        .with_cpu(CpuRefreshKind::everything())
        .with_memory(MemoryRefreshKind::everything())
        .with_processes(ProcessRefreshKind::everything());

    let mut sys = System::new_with_specifics(refresh_kind);

    // api_client is Option — None until registration succeeds.
    // Built inside the loop so registration is retried every cycle.
    let mut api_client: Option<api::ApiClient> = if let Some(key) = cfg.api_key.clone() {
        match api::ApiClient::new(&cfg, key) {
            Ok(c) => Some(c),
            Err(e) => {
                warn!("Could not build API client from saved key: {:#}", e);
                None
            }
        }
    } else {
        None
    };

    let mut last_latency: Option<u64> = None;
    let interval = Duration::from_secs(cfg.ingest_interval_secs);

    let mut status = ipc::ProbeStatus {
        server_url: cfg.server_url.clone(),
        company_token_hint: format!(
            "{}...",
            cfg.company_token.chars().take(8).collect::<String>()
        ),
        machine_id: cfg.machine_id.clone(),
        service_version: config::APP_VERSION.to_string(),
        ..Default::default()
    };

    let mut batch: Vec<collectors::MetricSnapshot> = Vec::new();

    while running.load(Ordering::SeqCst) {
        let loop_start = Instant::now();

        // ── Registration retry — runs every cycle until we have an api_client ──
        if api_client.is_none() {
            info!("No API key — attempting registration with server...");
            match do_register(&cfg).await {
                Ok((key, id)) => {
                    info!("Registration successful — machine_id={}", id);
                    cfg.api_key = Some(key.clone());
                    cfg.machine_id = Some(id.clone());
                    status.machine_id = Some(id);
                    if let Err(e) = config::save_config(&cfg) {
                        warn!("Could not save config after registration: {:#}", e);
                    }
                    match api::ApiClient::new(&cfg, key) {
                        Ok(c) => { api_client = Some(c); }
                        Err(e) => { error!("Could not build API client after registration: {:#}", e); }
                    }
                }
                Err(e) => {
                    // Log the full error chain so we can see the root cause
                    error!("Registration failed (will retry in {}s): {:#}", cfg.ingest_interval_secs, e);
                    status.connected = false;
                    status.error_message = Some(format!("Registration failed: {:#}", e));
                    let _ = ipc::write_status(&status);
                    let elapsed = loop_start.elapsed();
                    if elapsed < interval {
                        tokio::time::sleep(interval - elapsed).await;
                    }
                    continue;
                }
            }
        }

        sys.refresh_specifics(refresh_kind);

        let mut snapshot = collectors::collect_all(&sys);
        snapshot.net_latency_ms = last_latency;

        // Update status for tray
        status.cpu_percent = snapshot.cpu_percent;
        status.ram_percent = snapshot.ram_percent;
        status.disk_percent = snapshot.disk_usage.first().map(|d| d.percent).unwrap_or(0.0);
        status.latency_ms = last_latency;

        batch.push(snapshot);
        // Cap batch at 10 (avoid unbounded growth during outage)
        if batch.len() > 10 {
            batch.drain(0..batch.len() - 10);
        }

        if let Some(client) = &api_client {
            let to_send: Vec<_> = batch.drain(..).collect();
            match client.ingest(to_send).await {
                Ok(latency) => {
                    last_latency = Some(latency);
                    status.connected = true;
                    status.last_metric_sent = Some(chrono::Utc::now());
                    status.error_message = None;
                    info!("Metrics sent ({}ms)", latency);
                }
                Err(e) => {
                    status.connected = false;
                    status.error_message = Some(format!("{:#}", e));
                    last_latency = None;
                    warn!("Send failed: {:#}", e);
                    // If we get a 401, our api_key was revoked — clear it so we re-register
                    if e.to_string().contains("401") {
                        warn!("API key rejected (401) — clearing key and will re-register");
                        cfg.api_key = None;
                        cfg.machine_id = None;
                        api_client = None;
                        status.machine_id = None;
                        if let Err(se) = config::save_config(&cfg) {
                            warn!("Could not clear config: {:#}", se);
                        }
                    }
                }
            }
        }

        let _ = ipc::write_status(&status);

        let elapsed = loop_start.elapsed();
        if elapsed < interval {
            tokio::time::sleep(interval - elapsed).await;
        }
    }

    Ok(())
}

async fn do_register(cfg: &config::ProbeConfig) -> Result<(String, String)> {
    use crate::api::{register, RegisterRequest};
    use sysinfo::{CpuRefreshKind, MemoryRefreshKind, RefreshKind};

    let hostname = System::host_name().unwrap_or_else(|| "unknown".into());
    let os_ver = System::long_os_version().unwrap_or_else(|| "Windows".into());

    let cpu_sys = System::new_with_specifics(
        RefreshKind::new().with_cpu(CpuRefreshKind::everything()),
    );
    let cpu_model = cpu_sys
        .cpus()
        .first()
        .map(|c| c.brand().to_string())
        .unwrap_or_else(|| "Unknown CPU".into());

    let mem_sys = System::new_with_specifics(
        RefreshKind::new().with_memory(MemoryRefreshKind::everything()),
    );
    let total_ram_gb = mem_sys.total_memory() as f64 / 1_073_741_824.0;

    let req = RegisterRequest {
        hostname,
        os_version: os_ver,
        cpu_model,
        total_ram_gb,
        ip_address: local_ip(),
        mac_address: mac_address(),
        company_token: cfg.company_token.clone(),
    };

    // register() now returns (api_key, machine_id_string) directly
    register(cfg, req).await
}

fn local_ip() -> String {
    use std::net::UdpSocket;
    UdpSocket::bind("0.0.0.0:0")
        .and_then(|s| {
            s.connect("8.8.8.8:80")?;
            s.local_addr()
        })
        .map(|a| a.ip().to_string())
        .unwrap_or_else(|_| "127.0.0.1".into())
}

fn mac_address() -> String {
    let networks = sysinfo::Networks::new_with_refreshed_list();
    for (name, data) in &networks {
        if !name.contains("lo") {
            let mac = data.mac_address().to_string();
            if mac != "00:00:00:00:00:00" {
                return mac;
            }
        }
    }
    "00:00:00:00:00:00".into()
}
