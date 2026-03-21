use sysinfo::System;

pub struct MemInfo {
    pub ram_percent: f32,
    pub ram_used_gb: f64,
    pub ram_total_gb: f64,
    pub swap_percent: f32,
    pub swap_used_gb: f64,
}

pub fn collect(sys: &System) -> MemInfo {
    let total = sys.total_memory();
    let used = sys.used_memory();
    let ram_percent = if total > 0 {
        (used as f64 / total as f64 * 100.0) as f32
    } else {
        0.0
    };

    let swap_total = sys.total_swap();
    let swap_used = sys.used_swap();
    let swap_percent = if swap_total > 0 {
        (swap_used as f64 / swap_total as f64 * 100.0) as f32
    } else {
        0.0
    };

    const GB: f64 = 1_073_741_824.0;

    MemInfo {
        ram_percent,
        ram_used_gb: used as f64 / GB,
        ram_total_gb: total as f64 / GB,
        swap_percent,
        swap_used_gb: swap_used as f64 / GB,
    }
}
