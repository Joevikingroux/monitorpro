use sysinfo::System;

pub struct CpuInfo {
    pub overall: f32,
    pub per_core: Vec<f32>,
    pub freq_mhz: Option<u64>,
}

pub fn collect(sys: &System) -> CpuInfo {
    let overall = sys.global_cpu_info().cpu_usage();
    let per_core: Vec<f32> = sys.cpus().iter().map(|c| c.cpu_usage()).collect();
    let freq_mhz = sys.cpus().first().map(|c| c.frequency());

    CpuInfo {
        overall,
        per_core,
        freq_mhz,
    }
}

/// Try to read CPU temperature from sysinfo Components (may return None if
/// no sensor data is available — this is normal on many Windows systems).
pub fn read_temp() -> Option<f32> {
    use sysinfo::Components;
    let components = Components::new_with_refreshed_list();
    components
        .iter()
        .find(|c| {
            let label = c.label().to_lowercase();
            label.contains("cpu") || label.contains("core 0") || label.contains("package")
        })
        .map(|c| c.temperature())
}
