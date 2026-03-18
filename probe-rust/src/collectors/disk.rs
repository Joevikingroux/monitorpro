use crate::collectors::DiskInfo;
use sysinfo::Disks;

pub fn collect() -> Vec<DiskInfo> {
    let disks = Disks::new_with_refreshed_list();
    const GB: f64 = 1_073_741_824.0;

    disks
        .iter()
        .filter(|d| {
            // Only real drives — skip network, optical, RAM disks
            let kind = format!("{:?}", d.kind());
            !kind.contains("Unknown") && d.total_space() > 0
        })
        .map(|d| {
            let total = d.total_space() as f64;
            let avail = d.available_space() as f64;
            let used = total - avail;
            let percent = if total > 0.0 {
                (used / total * 100.0) as f32
            } else {
                0.0
            };

            DiskInfo {
                name: d.name().to_string_lossy().to_string(),
                mount: d.mount_point().to_string_lossy().to_string(),
                total_gb: total / GB,
                used_gb: used / GB,
                free_gb: avail / GB,
                percent,
                read_mb_s: None,  // TODO: disk I/O counters require platform API
                write_mb_s: None,
            }
        })
        .collect()
}
