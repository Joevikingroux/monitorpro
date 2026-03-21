use sysinfo::Networks;

pub struct NetInfo {
    pub sent_mb: f64,
    pub recv_mb: f64,
}

pub fn collect() -> NetInfo {
    let networks = Networks::new_with_refreshed_list();
    const MB: f64 = 1_048_576.0;

    let mut total_sent = 0u64;
    let mut total_recv = 0u64;

    for (_iface, data) in &networks {
        total_sent += data.total_transmitted();
        total_recv += data.total_received();
    }

    NetInfo {
        sent_mb: total_sent as f64 / MB,
        recv_mb: total_recv as f64 / MB,
    }
}
