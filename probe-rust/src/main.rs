//! Numbers10 PCMonitor Probe — entry point.
//!
//! EXE modes (detected from args):
//!   (no args)       → installer GUI (or "already installed" GUI if detected)
//!   --run-service   → Windows Service mode (called by SCM)
//!   --tray          → System tray app (called by registry Run key at login)

#![windows_subsystem = "windows"]

mod api;
mod collectors;
mod config;
mod installer;
mod installer_gui;
mod ipc;
mod service;
mod status_window;
mod tray;

fn setup_logging() {
    use log::LevelFilter;
    use log4rs::{
        append::file::FileAppender,
        config::{Appender, Config, Root},
        encode::pattern::PatternEncoder,
    };

    let log_path = config::log_path();
    if let Some(parent) = log_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    let Ok(appender) = FileAppender::builder()
        .encoder(Box::new(PatternEncoder::new(
            "{d(%Y-%m-%d %H:%M:%S)} [{l}] {m}{n}",
        )))
        .build(&log_path)
    else {
        return;
    };

    let Ok(config) = Config::builder()
        .appender(Appender::builder().build("file", Box::new(appender)))
        .build(Root::builder().appender("file").build(LevelFilter::Info))
    else {
        return;
    };

    let _ = log4rs::init_config(config);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    // ── Windows Service (called by SCM via `sc start`) ─────────────────────
    if args.iter().any(|a| a == "--run-service") {
        setup_logging();
        let _ = service::start();
        return;
    }

    // ── Tray daemon (called by registry Run key at login) ──────────────────
    if args.iter().any(|a| a == "--tray") {
        tray::run();     // simple loop — no logging needed, exits via process::exit
        return;
    }

    // ── Status window (spawned by tray daemon on click) ────────────────────
    if args.iter().any(|a| a == "--status") {
        status_window::run();
        return;
    }

    // ── Default: GUI installer / uninstaller ───────────────────────────────
    // Detects installed state automatically and shows the right page.
    // Requires admin for install; no extra args needed.
    installer_gui::run();
}
