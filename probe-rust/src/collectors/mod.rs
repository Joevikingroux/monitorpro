pub mod cpu;
pub mod disk;
pub mod memory;
pub mod network;
pub mod windows_ext;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sysinfo::System;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiskInfo {
    pub name: String,
    pub mount: String,
    pub total_gb: f64,
    pub used_gb: f64,
    pub free_gb: f64,
    pub percent: f32,
    pub read_mb_s: Option<f64>,
    pub write_mb_s: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessInfo {
    pub pid: u32,
    pub name: String,
    pub cpu_pct: f32,
    pub ram_mb: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricSnapshot {
    pub collected_at: DateTime<Utc>,

    // CPU
    pub cpu_percent: f32,
    pub cpu_freq_mhz: Option<u64>,
    pub cpu_temp_c: Option<f32>,
    pub per_core_percent: Vec<f32>,

    // Memory
    pub ram_percent: f32,
    pub ram_used_gb: f64,
    pub ram_total_gb: f64,
    pub swap_percent: f32,
    pub swap_used_gb: f64,

    // Disk
    pub disk_usage: Vec<DiskInfo>,

    // Network
    pub net_sent_mb: f64,
    pub net_recv_mb: f64,
    pub net_latency_ms: Option<u64>,

    // GPU (optional)
    pub gpu_percent: Option<f32>,
    pub gpu_temp_c: Option<f32>,
    pub gpu_vram_used_mb: Option<f64>,

    // Top processes
    pub top_processes: Vec<ProcessInfo>,

    // Security (refreshed every 5 min, cached between cycles)
    pub firewall_enabled: Option<bool>,
    pub av_status: Option<String>,
    pub last_boot_time: Option<chrono::DateTime<chrono::Utc>>,
    pub installed_updates: Option<u32>,
}

/// Collect all metrics. `sys` must have been refreshed by caller.
pub fn collect_all(sys: &System) -> MetricSnapshot {
    let cpu_info = cpu::collect(sys);
    let cpu_temp = cpu::read_temp(); // separate Components refresh
    let mem_info = memory::collect(sys);
    let disks = disk::collect();
    let net_info = network::collect();

    let mut procs: Vec<ProcessInfo> = sys
        .processes()
        .values()
        .map(|p| ProcessInfo {
            pid: p.pid().as_u32(),
            name: p.name().to_string(),
            cpu_pct: p.cpu_usage(),
            ram_mb: p.memory() as f64 / 1_048_576.0,
        })
        .collect();
    procs.sort_by(|a, b| b.cpu_pct.partial_cmp(&a.cpu_pct).unwrap());
    procs.truncate(10);

    MetricSnapshot {
        collected_at: Utc::now(),
        cpu_percent: cpu_info.overall,
        cpu_freq_mhz: cpu_info.freq_mhz,
        cpu_temp_c: cpu_temp,
        per_core_percent: cpu_info.per_core,
        ram_percent: mem_info.ram_percent,
        ram_used_gb: mem_info.ram_used_gb,
        ram_total_gb: mem_info.ram_total_gb,
        swap_percent: mem_info.swap_percent,
        swap_used_gb: mem_info.swap_used_gb,
        disk_usage: disks,
        net_sent_mb: net_info.sent_mb,
        net_recv_mb: net_info.recv_mb,
        net_latency_ms: None, // filled in by service after API call
        gpu_percent: None,
        gpu_temp_c: None,
        gpu_vram_used_mb: None,
        top_processes: procs,
        firewall_enabled: None,
        av_status: None,
        last_boot_time: None,
        installed_updates: None,
    }
}
