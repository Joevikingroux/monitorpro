/// Tray daemon — runs in the user session (--tray flag).
/// Uses a simple 50ms polling loop with NO eframe.
/// Status window is opened as a separate --status subprocess so it can
/// be closed and reopened freely without any eframe visibility issues.

use image::{ImageBuffer, Rgba, RgbaImage};
use tray_icon::{
    menu::{Menu, MenuEvent, MenuItem, PredefinedMenuItem},
    Icon, TrayIconBuilder, TrayIconEvent,
};

use crate::config;

static LOGO_BYTES: &[u8] = include_bytes!("../assets/logo.png");

const TEAL: [u8; 4] = [45, 212, 191, 255];
const RED_RGBA: [u8; 4] = [239, 68, 68, 255];

// ── Tray icon compositing ──────────────────────────────────────────────────

fn make_icon_rgba(connected: bool) -> Vec<u8> {
    let logo = image::load_from_memory(LOGO_BYTES).unwrap_or_else(|_| {
        image::DynamicImage::ImageRgba8(ImageBuffer::from_fn(32, 32, |_, _| {
            Rgba([45u8, 212, 191, 255])
        }))
    });

    let mut img: RgbaImage = logo
        .resize_exact(32, 32, image::imageops::FilterType::Lanczos3)
        .to_rgba8();

    let arrow_color = if connected { TEAL } else { RED_RGBA };
    let ax = 22u32;
    let ay = 22u32;
    let size = 10u32;

    for row in 0..size {
        let half_w = if connected {
            (row + 1).min(size / 2 + 1)
        } else {
            (size - row).min(size / 2 + 1)
        };
        let left = (size / 2).saturating_sub(half_w / 2);
        let right = left + half_w;
        for col in left..right {
            let px = ax + col;
            let py = ay + (if connected { size - 1 - row } else { row });
            if px < 32 && py < 32 {
                img.put_pixel(px, py, Rgba(arrow_color));
            }
        }
    }

    img.into_raw()
}

fn build_icon(connected: bool) -> Icon {
    Icon::from_rgba(make_icon_rgba(connected), 32, 32).expect("Icon build failed")
}

// ── Bring an already-open status window to the foreground ─────────────────

fn bring_status_to_front() {
    use std::ptr;
    let title = b"Numbers10 PCMonitor - Status\0";
    unsafe {
        let hwnd = winapi::um::winuser::FindWindowA(
            ptr::null(),
            title.as_ptr() as *const i8,
        );
        if !hwnd.is_null() {
            winapi::um::winuser::ShowWindow(hwnd, winapi::um::winuser::SW_RESTORE);
            winapi::um::winuser::SetForegroundWindow(hwnd);
        }
    }
}

// ── Open/focus the status window ──────────────────────────────────────────

fn open_status_window(child: &mut Option<std::process::Child>) {
    // If the child process is still alive, just bring it to front
    if let Some(c) = child.as_mut() {
        if c.try_wait().ok().flatten().is_none() {
            bring_status_to_front();
            return;
        }
    }
    // Spawn a fresh status window subprocess
    if let Ok(exe) = std::env::current_exe() {
        *child = std::process::Command::new(exe).arg("--status").spawn().ok();
    }
}

// ── Entry point ───────────────────────────────────────────────────────────

pub fn run() {
    // ── Build context menu ────────────────────────────────────────────────
    let header  = MenuItem::new("Numbers10 PCMonitor", false, None);
    let sep1    = PredefinedMenuItem::separator();
    let open    = MenuItem::new("Open Status", true, None);
    let sep2    = PredefinedMenuItem::separator();
    let logs    = MenuItem::new("View Logs", true, None);
    let restart = MenuItem::new("Restart Service", true, None);
    let sep3    = PredefinedMenuItem::separator();
    let quit    = MenuItem::new("Exit Tray", true, None);

    let open_id    = open.id().clone();
    let logs_id    = logs.id().clone();
    let restart_id = restart.id().clone();
    let quit_id    = quit.id().clone();

    let menu = Menu::new();
    let _ = menu.append(&header);
    let _ = menu.append(&sep1);
    let _ = menu.append(&open);
    let _ = menu.append(&sep2);
    let _ = menu.append(&logs);
    let _ = menu.append(&restart);
    let _ = menu.append(&sep3);
    let _ = menu.append(&quit);

    // ── Build tray icon ───────────────────────────────────────────────────
    let tray = TrayIconBuilder::new()
        .with_menu(Box::new(menu))
        .with_tooltip(config::TRAY_TOOLTIP)
        .with_icon(build_icon(false))
        .build()
        .expect("Failed to create tray icon");

    let mut status_child: Option<std::process::Child> = None;
    let mut last_connected = false;
    let mut last_icon_check = std::time::Instant::now();

    // ── Main event loop ───────────────────────────────────────────────────
    // tray-icon on Windows requires a Windows message pump on this thread.
    // PeekMessage + DispatchMessage drives the hidden tray window's message
    // queue. Without this, right-click and click events never fire.
    loop {
        // Pump Windows messages first
        unsafe {
            let mut msg: winapi::um::winuser::MSG = std::mem::zeroed();
            while winapi::um::winuser::PeekMessageW(
                &mut msg,
                std::ptr::null_mut(),
                0,
                0,
                winapi::um::winuser::PM_REMOVE,
            ) != 0 {
                winapi::um::winuser::TranslateMessage(&msg);
                winapi::um::winuser::DispatchMessageW(&msg);
            }
        }

        // Drain tray click events
        while let Ok(event) = TrayIconEvent::receiver().try_recv() {
            if let TrayIconEvent::Click { button, button_state, .. } = event {
                use tray_icon::{MouseButton, MouseButtonState};
                if button == MouseButton::Left && button_state == MouseButtonState::Up {
                    open_status_window(&mut status_child);
                }
            }
        }

        // Drain menu events
        while let Ok(ev) = MenuEvent::receiver().try_recv() {
            if ev.id == quit_id {
                // Kill status window if open, then exit cleanly
                if let Some(child) = status_child.as_mut() {
                    let _ = child.kill();
                }
                drop(tray); // remove tray icon before exit
                std::process::exit(0);
            } else if ev.id == open_id {
                open_status_window(&mut status_child);
            } else if ev.id == logs_id {
                let path = config::log_path();
                if path.exists() {
                    let _ = std::process::Command::new("notepad.exe").arg(&path).spawn();
                }
            } else if ev.id == restart_id {
                let _ = std::process::Command::new("sc.exe")
                    .args(["stop", config::SERVICE_NAME])
                    .status();
                std::thread::sleep(std::time::Duration::from_secs(2));
                let _ = std::process::Command::new("sc.exe")
                    .args(["start", config::SERVICE_NAME])
                    .spawn();
            }
        }

        // Update tray icon if connection status changed (every 5s)
        if last_icon_check.elapsed().as_secs() >= 5 {
            last_icon_check = std::time::Instant::now();
            let connected = crate::ipc::read_status()
                .map(|s| s.connected)
                .unwrap_or(false);
            if connected != last_connected {
                last_connected = connected;
                let _ = tray.set_icon(Some(build_icon(connected)));
                let tip = if connected {
                    format!("{} — Connected", config::TRAY_TOOLTIP)
                } else {
                    format!("{} — DISCONNECTED", config::TRAY_TOOLTIP)
                };
                let _ = tray.set_tooltip(Some(tip));
            }
        }

        std::thread::sleep(std::time::Duration::from_millis(50));
    }
}
