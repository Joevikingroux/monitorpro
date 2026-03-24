/// Proper GUI installer / uninstaller wizard.
/// Run with no args → auto-detects installed state and shows correct page.

use eframe::egui;
use std::sync::mpsc::{channel, Receiver};

use crate::{config, installer};

static LOGO_BYTES: &[u8] = include_bytes!("../assets/logo.png");

// ── Colours ───────────────────────────────────────────────────────────────
const BG: egui::Color32 = egui::Color32::from_rgb(0, 0, 0);
const SURFACE: egui::Color32 = egui::Color32::from_rgb(5, 10, 18);
const CARD: egui::Color32 = egui::Color32::from_rgb(10, 18, 32);
const TEXT: egui::Color32 = egui::Color32::from_rgb(224, 247, 250);
const SECONDARY: egui::Color32 = egui::Color32::from_rgb(148, 163, 184);
const MUTED: egui::Color32 = egui::Color32::from_rgb(100, 116, 139);
const TEAL: egui::Color32 = egui::Color32::from_rgb(45, 212, 191);
const RED: egui::Color32 = egui::Color32::from_rgb(239, 68, 68);

// ── Pages ─────────────────────────────────────────────────────────────────

#[derive(Clone, PartialEq)]
enum Page {
    Welcome,
    Configure,
    Installing,
    InstallSuccess,
    InstallFailed,
    AlreadyInstalled,
    Uninstalling,
    UninstallDone,
    ResettingRegistration,
    ResetDone,
}

// ── App ───────────────────────────────────────────────────────────────────

struct InstallerApp {
    page: Page,
    logo: Option<egui::TextureHandle>,
    logo_aspect: f32, // height / width

    // Form fields
    server_url: String,
    company_token: String,
    company_token_visible: bool,

    // Install/uninstall progress
    log_lines: Vec<String>,
    rx: Option<Receiver<String>>,
    progress_t: f32,
    anim_t: f32,
    error_msg: String,

    // Existing install info
    existing_server: String,
    existing_company_hint: String,
    existing_running: bool,

    /// True when a token is baked in and install should start automatically
    /// without showing the Welcome / Configure screens.
    auto_install: bool,
}

impl InstallerApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        apply_theme(&cc.egui_ctx);
        let (logo, logo_aspect) = load_logo(&cc.egui_ctx);

        let server_url = config::BAKED_SERVER_URL
            .unwrap_or(config::DEFAULT_SERVER_URL)
            .to_string();
        let company_token = config::BAKED_COMPANY_TOKEN.unwrap_or("").to_string();

        if installer::is_installed() {
            let cfg = config::load_config().unwrap_or_default();
            let running = installer::service_is_running();
            let hint = format!(
                "{}...",
                cfg.company_token.chars().take(8).collect::<String>()
            );
            Self {
                page: Page::AlreadyInstalled,
                logo,
                logo_aspect,
                server_url,
                company_token,
                company_token_visible: false,
                log_lines: Vec::new(),
                rx: None,
                progress_t: 0.0,
                anim_t: 0.0,
                error_msg: String::new(),
                existing_server: cfg.server_url,
                existing_company_hint: hint,
                existing_running: running,
                auto_install: false,
            }
        } else {
            // If a company token is baked into this EXE, skip the wizard and
            // install automatically as soon as the first frame renders.
            // Only auto-install if token is a real token, not the build placeholder.
            let auto_install = !company_token.is_empty()
                && company_token != "X".repeat(64);
            Self {
                page: if auto_install { Page::Installing } else { Page::Welcome },
                logo,
                logo_aspect,
                server_url,
                company_token,
                company_token_visible: false,
                log_lines: Vec::new(),
                rx: None,
                progress_t: 0.0,
                anim_t: 0.0,
                error_msg: String::new(),
                existing_server: String::new(),
                existing_company_hint: String::new(),
                existing_running: false,
                auto_install,
            }
        }
    }

    fn begin_install(&mut self) {
        self.log_lines.clear();
        self.progress_t = 0.0;
        self.error_msg = String::new();
        self.page = Page::Installing;

        let (tx, rx) = channel::<String>();
        self.rx = Some(rx);

        let server = self.server_url.clone();
        let company = self.company_token.clone();

        std::thread::spawn(move || {
            let result = installer::install_with_progress(&server, &company, true, |msg| {
                let _ = tx.send(msg.to_string());
            });
            match result {
                Err(e) => {
                    let _ = tx.send(format!("ERROR: {}", e));
                }
                Ok(()) => {
                    // ── Wait for service to register with the server ────────
                    let _ = tx.send("Waiting for probe to connect and register...".to_string());
                    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(120);
                    let mut registered = false;
                    let mut dots = 0u32;

                    while std::time::Instant::now() < deadline {
                        std::thread::sleep(std::time::Duration::from_secs(3));

                        if let Some(status) = crate::ipc::read_status() {
                            if status.connected && status.machine_id.is_some() {
                                let mid = status.machine_id.unwrap();
                                let _ = tx.send(format!(
                                    "✓ Connected! Machine ID: {}  ({} ms latency)",
                                    mid,
                                    status.latency_ms.unwrap_or(0)
                                ));
                                registered = true;
                                break;
                            } else if let Some(err) = &status.error_message {
                                dots += 1;
                                let _ = tx.send(format!(
                                    "  Connecting{}  ({})",
                                    ".".repeat((dots % 3 + 1) as usize),
                                    err
                                ));
                            } else {
                                dots += 1;
                                let _ = tx.send(format!(
                                    "  Connecting{}",
                                    ".".repeat((dots % 3 + 1) as usize)
                                ));
                            }
                        } else {
                            dots += 1;
                            let _ = tx.send(format!(
                                "  Starting service{}",
                                ".".repeat((dots % 3 + 1) as usize)
                            ));
                        }
                    }

                    if registered {
                        let _ = tx.send("DONE: Installation complete! Service is running and connected.".to_string());
                    } else {
                        let _ = tx.send("DONE: Installed — service running but could not confirm registration (check server URL and token, or view logs).".to_string());
                    }
                }
            }
        });
    }

    fn begin_reset(&mut self) {
        self.log_lines.clear();
        self.progress_t = 0.0;
        self.error_msg = String::new();
        self.page = Page::ResettingRegistration;

        let (tx, rx) = channel::<String>();
        self.rx = Some(rx);

        std::thread::spawn(move || {
            let result = installer::reset_registration(|msg| {
                let _ = tx.send(msg.to_string());
            });
            if let Err(e) = result {
                let _ = tx.send(format!("ERROR: {}", e));
            }
        });
    }

    fn begin_uninstall(&mut self) {
        self.log_lines.clear();
        self.progress_t = 0.0;
        self.error_msg = String::new();
        self.page = Page::Uninstalling;

        let (tx, rx) = channel::<String>();
        self.rx = Some(rx);

        std::thread::spawn(move || {
            let result = installer::uninstall_with_progress(|msg| {
                let _ = tx.send(msg.to_string());
            });
            if let Err(e) = result {
                let _ = tx.send(format!("ERROR: {}", e));
            }
        });
    }
}

impl eframe::App for InstallerApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Auto-install: baked token present, kick off install on first frame.
        if self.auto_install && self.rx.is_none() {
            self.auto_install = false;
            self.begin_install();
        }

        self.anim_t += ctx.input(|i| i.stable_dt);

        // ── Drain progress channel ─────────────────────────────────────────
        if let Some(rx) = &self.rx {
            while let Ok(msg) = rx.try_recv() {
                if msg.starts_with("DONE") {
                    self.progress_t = 1.0;
                    self.log_lines.push(msg);
                    self.page = match self.page {
                        Page::Installing => Page::InstallSuccess,
                        Page::Uninstalling => Page::UninstallDone,
                        Page::ResettingRegistration => Page::ResetDone,
                        _ => self.page.clone(),
                    };
                } else if msg.starts_with("ERROR:") {
                    self.error_msg = msg[6..].trim().to_string();
                    self.log_lines.push(msg);
                    if self.page == Page::Installing {
                        self.page = Page::InstallFailed;
                    }
                } else {
                    self.log_lines.push(msg);
                }
            }
        }

        // Animate progress bar
        if matches!(self.page, Page::Installing | Page::Uninstalling | Page::ResettingRegistration) && self.progress_t < 0.93 {
            self.progress_t = (self.progress_t + 0.004).min(0.93);
        }

        egui::CentralPanel::default()
            .frame(egui::Frame::none().fill(BG))
            .show(ctx, |ui| {
                let page = self.page.clone();
                match page {
                    Page::Welcome => self.draw_welcome(ui, ctx),
                    Page::Configure => self.draw_configure(ui, ctx),
                    Page::Installing => self.draw_progress(ui, "Installing..."),
                    Page::InstallSuccess => self.draw_install_success(ui, ctx),
                    Page::InstallFailed => self.draw_install_failed(ui, ctx),
                    Page::AlreadyInstalled => self.draw_already_installed(ui, ctx),
                    Page::Uninstalling => self.draw_progress(ui, "Uninstalling..."),
                    Page::UninstallDone => self.draw_uninstall_done(ui, ctx),
                    Page::ResettingRegistration => self.draw_progress(ui, "Resetting Registration..."),
                    Page::ResetDone => self.draw_reset_done(ui, ctx),
                }
            });

        ctx.request_repaint_after(std::time::Duration::from_millis(50));
    }
}

// ── Page renders ──────────────────────────────────────────────────────────

impl InstallerApp {
    fn draw_welcome(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        centered_column(ui, 420.0, |ui| {
            ui.add_space(32.0);
            self.show_logo(ui, 180.0);
            ui.add_space(20.0);

            ui.label(
                egui::RichText::new("Numbers10 PCMonitor")
                    .color(TEXT)
                    .size(26.0)
                    .strong(),
            );
            ui.label(
                egui::RichText::new("Probe Agent")
                    .color(TEAL)
                    .size(14.0),
            );
            ui.add_space(4.0);
            ui.label(
                egui::RichText::new(format!("Version {}", config::APP_VERSION))
                    .color(MUTED)
                    .size(11.0),
            );

            ui.add_space(24.0);
            divider(ui);
            ui.add_space(16.0);

            card(ui, |ui| {
                ui.label(egui::RichText::new("This installer will:").color(SECONDARY).size(13.0));
                ui.add_space(6.0);
                bullet(ui, "Copy the probe to Program Files");
                bullet(ui, "Install as a Windows Service (Delayed Auto Start)");
                bullet(ui, "Start the service automatically");
                bullet(ui, "Add tray icon to login startup");
            });

            ui.add_space(24.0);

            if teal_button(ui, "  NEXT  →  ", 420.0) {
                self.page = Page::Configure;
            }

            ui.add_space(8.0);
            ui.horizontal(|ui| {
                ui.add_space((420.0 - 60.0) / 2.0);
                if ui
                    .add(egui::Button::new(egui::RichText::new("Cancel").color(MUTED)).frame(false))
                    .clicked()
                {
                    std::process::exit(0);
                }
            });
        });
    }

    fn draw_configure(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        centered_column(ui, 420.0, |ui| {
            ui.add_space(24.0);
            self.show_logo(ui, 100.0);
            ui.add_space(16.0);

            ui.label(egui::RichText::new("Configuration").color(TEXT).size(22.0).strong());
            ui.label(egui::RichText::new("Enter the server details provided by your admin.").color(SECONDARY).size(12.0));
            ui.add_space(20.0);

            // Server URL
            field_label(ui, "Server URL");
            egui::Frame::none()
                .fill(CARD)
                .rounding(egui::Rounding::same(6.0))
                .inner_margin(egui::Margin::symmetric(10.0, 6.0))
                .stroke(egui::Stroke::new(0.667, egui::Color32::from_rgba_unmultiplied(45, 212, 191, 40)))
                .show(ui, |ui| {
                    ui.add(
                        egui::TextEdit::singleline(&mut self.server_url)
                            .desired_width(f32::INFINITY)
                            .text_color(TEXT)
                            .frame(false)
                            .hint_text("https://monitor.company.com:8443"),
                    );
                });

            ui.add_space(12.0);

            // Company Token
            field_label(ui, "Company Token");
            egui::Frame::none()
                .fill(CARD)
                .rounding(egui::Rounding::same(6.0))
                .inner_margin(egui::Margin::symmetric(10.0, 6.0))
                .stroke(egui::Stroke::new(0.667, egui::Color32::from_rgba_unmultiplied(45, 212, 191, 40)))
                .show(ui, |ui| {
                    ui.horizontal(|ui| {
                        let edit = egui::TextEdit::singleline(&mut self.company_token)
                            .desired_width(ui.available_width() - 60.0)
                            .text_color(TEXT)
                            .frame(false)
                            .password(!self.company_token_visible)
                            .hint_text("Paste token from dashboard");
                        ui.add(edit);
                        let eye = if self.company_token_visible { "👁" } else { "🙈" };
                        if ui.small_button(eye).clicked() {
                            self.company_token_visible = !self.company_token_visible;
                        }
                    });
                });

            ui.add_space(10.0);

            // Validation
            let server_ok = !self.server_url.is_empty()
                && (self.server_url.starts_with("http://") || self.server_url.starts_with("https://"));
            let token_ok = self.company_token.len() >= 8;

            if !server_ok && !self.server_url.is_empty() {
                ui.add_space(4.0);
                ui.label(egui::RichText::new("⚠  Server URL must start with https://").color(RED).size(11.0));
            }
            if !token_ok && !self.company_token.is_empty() {
                ui.add_space(4.0);
                ui.label(egui::RichText::new("⚠  Token looks too short — check the dashboard").color(RED).size(11.0));
            }

            ui.add_space(24.0);

            ui.horizontal(|ui| {
                if outline_button(ui, "← Back", 100.0) {
                    self.page = Page::Welcome;
                }
                ui.add_space(8.0);
                let ready = server_ok && token_ok;
                ui.add_enabled_ui(ready, |ui| {
                    if teal_button(ui, "  INSTALL  →", 304.0) {
                        self.begin_install();
                    }
                });
            });

            if !token_ok && self.company_token.is_empty() {
                ui.add_space(4.0);
                ui.label(egui::RichText::new("Get your company token from the dashboard → Companies → Copy Token").color(MUTED).size(11.0));
            }
        });
    }

    fn draw_progress(&mut self, ui: &mut egui::Ui, title: &str) {
        centered_column(ui, 420.0, |ui| {
            ui.add_space(32.0);
            self.show_logo(ui, 80.0);
            ui.add_space(20.0);

            ui.label(egui::RichText::new(title).color(TEXT).size(22.0).strong());
            ui.add_space(4.0);
            ui.label(egui::RichText::new("Please wait, do not close this window.").color(SECONDARY).size(12.0));
            ui.add_space(20.0);

            // Animated progress bar
            let progress = self.progress_t;
            let (bar_rect, _) = ui.allocate_exact_size(egui::vec2(420.0, 8.0), egui::Sense::hover());
            ui.painter().rect_filled(bar_rect, egui::Rounding::same(4.0), CARD);
            let fill_w = bar_rect.width() * progress;
            if fill_w > 0.0 {
                let fill = egui::Rect::from_min_size(bar_rect.min, egui::vec2(fill_w, bar_rect.height()));
                ui.painter().rect_filled(fill, egui::Rounding::same(4.0), TEAL);
            }

            ui.add_space(12.0);

            // Log output
            egui::Frame::none()
                .fill(SURFACE)
                .rounding(egui::Rounding::same(8.0))
                .inner_margin(egui::Margin::same(12.0))
                .show(ui, |ui| {
                    ui.set_min_size(egui::vec2(420.0, 220.0));
                    egui::ScrollArea::vertical()
                        .max_height(220.0)
                        .stick_to_bottom(true)
                        .show(ui, |ui| {
                            for line in &self.log_lines {
                                let color = if line.starts_with("ERROR") { RED }
                                    else if line.starts_with("DONE") { TEAL }
                                    else { SECONDARY };
                                ui.label(
                                    egui::RichText::new(format!("▸  {}", line))
                                        .color(color)
                                        .size(12.0)
                                        .monospace(),
                                );
                            }
                        });
                });
        });
    }

    fn draw_install_success(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        centered_column(ui, 420.0, |ui| {
            ui.add_space(48.0);
            self.show_logo(ui, 100.0);
            ui.add_space(24.0);

            // Big tick
            ui.label(egui::RichText::new("✓").color(TEAL).size(56.0));
            ui.add_space(8.0);
            ui.label(egui::RichText::new("Installation Complete!").color(TEXT).size(24.0).strong());
            ui.add_space(8.0);
            ui.label(egui::RichText::new("The service is running and will start automatically on boot.\nThe tray icon will appear at your next login.").color(SECONDARY).size(13.0));

            ui.add_space(32.0);
            divider(ui);
            ui.add_space(16.0);

            if teal_button(ui, "  Launch Tray Icon Now  ", 420.0) {
                launch_tray();
                std::process::exit(0);
            }
            ui.add_space(8.0);
            if outline_button(ui, "Close Installer", 420.0) {
                std::process::exit(0);
            }
        });
    }

    fn draw_install_failed(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        centered_column(ui, 420.0, |ui| {
            ui.add_space(48.0);
            self.show_logo(ui, 80.0);
            ui.add_space(24.0);

            ui.label(egui::RichText::new("✗").color(RED).size(56.0));
            ui.add_space(8.0);
            ui.label(egui::RichText::new("Installation Failed").color(TEXT).size(24.0).strong());
            ui.add_space(12.0);

            egui::Frame::none()
                .fill(egui::Color32::from_rgba_unmultiplied(239, 68, 68, 20))
                .rounding(egui::Rounding::same(8.0))
                .inner_margin(egui::Margin::symmetric(16.0, 12.0))
                .show(ui, |ui| {
                    ui.label(
                        egui::RichText::new(&self.error_msg)
                            .color(RED)
                            .size(12.0),
                    );
                });

            ui.add_space(12.0);
            ui.label(egui::RichText::new("Make sure you are running as Administrator.").color(MUTED).size(12.0));
            ui.add_space(24.0);

            if outline_button(ui, "← Try Again", 200.0) {
                self.page = Page::Configure;
            }
            ui.add_space(8.0);
            if ui
                .add(egui::Button::new(egui::RichText::new("Close").color(MUTED)).frame(false))
                .clicked()
            {
                std::process::exit(1);
            }
        });
    }

    fn draw_already_installed(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        centered_column(ui, 420.0, |ui| {
            ui.add_space(32.0);
            self.show_logo(ui, 140.0);
            ui.add_space(16.0);

            ui.label(egui::RichText::new("Already Installed").color(TEXT).size(22.0).strong());

            // Status chip
            ui.add_space(8.0);
            let (status_text, status_color) = if self.existing_running {
                ("● Service Running", TEAL)
            } else {
                ("○ Service Stopped", RED)
            };
            egui::Frame::none()
                .fill(if self.existing_running {
                    egui::Color32::from_rgba_unmultiplied(45, 212, 191, 20)
                } else {
                    egui::Color32::from_rgba_unmultiplied(239, 68, 68, 20)
                })
                .rounding(egui::Rounding::same(20.0))
                .inner_margin(egui::Margin::symmetric(14.0, 6.0))
                .show(ui, |ui| {
                    ui.label(egui::RichText::new(status_text).color(status_color).size(12.0).strong());
                });

            ui.add_space(20.0);
            divider(ui);
            ui.add_space(12.0);

            // Current config details
            card(ui, |ui| {
                info_row(ui, "Server", &self.existing_server.clone());
                info_row(ui, "Company Token", &self.existing_company_hint.clone());
                info_row(ui, "Install Path", &config::install_dir().to_string_lossy().to_string());
                info_row(ui, "Config Path", &config::config_dir().to_string_lossy().to_string());
            });

            ui.add_space(20.0);

            // Launch tray button
            if teal_button(ui, "  Open Status Window  ", 420.0) {
                launch_tray();
            }

            ui.add_space(8.0);

            // Reset registration — useful if the server-side machine was deleted
            if outline_button(ui, "↺  Reset Registration", 420.0) {
                self.begin_reset();
            }
            ui.add_space(4.0);
            ui.label(
                egui::RichText::new(
                    "Use this if the machine was deleted from the dashboard — clears the saved API key so the probe re-registers fresh.",
                )
                .color(MUTED)
                .size(11.0),
            );

            ui.add_space(12.0);

            // Uninstall
            egui::Frame::none()
                .stroke(egui::Stroke::new(1.0, RED))
                .rounding(egui::Rounding::same(6.0))
                .inner_margin(egui::Margin::symmetric(0.0, 0.0))
                .show(ui, |ui| {
                    let btn = egui::Button::new(
                        egui::RichText::new("  Uninstall  ").color(RED).strong(),
                    )
                    .fill(egui::Color32::TRANSPARENT)
                    .rounding(egui::Rounding::same(6.0))
                    .min_size(egui::vec2(420.0, 36.0));
                    if ui.add(btn).clicked() {
                        self.begin_uninstall();
                    }
                });

            ui.add_space(8.0);
            ui.horizontal(|ui| {
                ui.add_space((420.0 - 60.0) / 2.0);
                if ui
                    .add(egui::Button::new(egui::RichText::new("Close").color(MUTED)).frame(false))
                    .clicked()
                {
                    std::process::exit(0);
                }
            });
        });
    }

    fn draw_uninstall_done(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        centered_column(ui, 420.0, |ui| {
            ui.add_space(56.0);
            self.show_logo(ui, 100.0);
            ui.add_space(24.0);

            ui.label(egui::RichText::new("✓").color(TEAL).size(56.0));
            ui.add_space(8.0);
            ui.label(egui::RichText::new("Uninstall Complete").color(TEXT).size(24.0).strong());
            ui.add_space(8.0);
            ui.label(
                egui::RichText::new("The service has been removed.\nYour config and logs are kept in %ProgramData%\\Numbers10\\PCMonitor\\")
                    .color(SECONDARY)
                    .size(12.0),
            );
            ui.add_space(32.0);

            if teal_button(ui, "  Close  ", 200.0) {
                std::process::exit(0);
            }
        });
    }

    fn draw_reset_done(&mut self, ui: &mut egui::Ui, _ctx: &egui::Context) {
        centered_column(ui, 420.0, |ui| {
            ui.add_space(56.0);
            self.show_logo(ui, 100.0);
            ui.add_space(24.0);

            ui.label(egui::RichText::new("↺").color(TEAL).size(56.0));
            ui.add_space(8.0);
            ui.label(egui::RichText::new("Registration Reset").color(TEXT).size(24.0).strong());
            ui.add_space(8.0);
            ui.label(
                egui::RichText::new(
                    "The saved API key has been cleared and the service restarted.\n\
                     The probe will re-register with the server automatically.",
                )
                .color(SECONDARY)
                .size(12.0),
            );
            ui.add_space(32.0);

            if teal_button(ui, "  Launch Tray Icon  ", 420.0) {
                launch_tray();
                std::process::exit(0);
            }
            ui.add_space(8.0);
            if outline_button(ui, "Close", 420.0) {
                std::process::exit(0);
            }
        });
    }

    fn show_logo(&self, ui: &mut egui::Ui, max_width: f32) {
        if let Some(tex) = &self.logo {
            let h = max_width * self.logo_aspect;
            let img = egui::Image::from_texture(egui::load::SizedTexture::new(
                tex.id(),
                egui::vec2(max_width, h),
            ))
            .max_width(max_width);
            ui.add(img);
        } else {
            // Fallback: teal diamond text
            ui.label(egui::RichText::new("◆ Numbers10").color(TEAL).size(28.0).strong());
        }
    }
}

// ── Entry point ───────────────────────────────────────────────────────────

fn load_icon() -> std::sync::Arc<egui::IconData> {
    if let Ok(img) = image::load_from_memory(LOGO_BYTES) {
        let rgba = img
            .resize_exact(64, 64, image::imageops::FilterType::Lanczos3)
            .to_rgba8();
        return std::sync::Arc::new(egui::IconData {
            rgba: rgba.into_raw(),
            width: 64,
            height: 64,
        });
    }
    std::sync::Arc::new(egui::IconData { rgba: vec![], width: 0, height: 0 })
}

pub fn run() {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("Numbers10 PCMonitor — Probe Setup")
            .with_inner_size([500.0, 620.0])
            .with_min_inner_size([500.0, 580.0])
            .with_resizable(false)
            .with_visible(true)
            .with_taskbar(true)
            .with_icon(load_icon()),
        centered: true,
        ..Default::default()
    };

    eframe::run_native(
        "Numbers10 PCMonitor Setup",
        native_options,
        Box::new(|cc| Box::new(InstallerApp::new(cc))),
    )
    .expect("Installer GUI failed");
}

// ── Helpers ───────────────────────────────────────────────────────────────

fn load_logo(ctx: &egui::Context) -> (Option<egui::TextureHandle>, f32) {
    match image::load_from_memory(LOGO_BYTES) {
        Ok(img) => {
            let rgba = img.to_rgba8();
            let (w, h) = (rgba.width() as usize, rgba.height() as usize);
            let aspect = h as f32 / w as f32;
            let pixels = rgba.into_raw();
            let tex = ctx.load_texture(
                "logo",
                egui::ColorImage::from_rgba_unmultiplied([w, h], &pixels),
                egui::TextureOptions::LINEAR,
            );
            (Some(tex), aspect)
        }
        Err(_) => (None, 0.3),
    }
}

fn apply_theme(ctx: &egui::Context) {
    let mut v = egui::Visuals::dark();
    v.window_fill = SURFACE;
    v.panel_fill = BG;
    v.faint_bg_color = CARD;
    v.extreme_bg_color = BG;
    v.window_stroke = egui::Stroke::new(0.667, egui::Color32::from_rgba_unmultiplied(45, 212, 191, 38));
    v.widgets.noninteractive.bg_fill = CARD;
    v.widgets.noninteractive.fg_stroke = egui::Stroke::new(1.0, SECONDARY);
    v.widgets.inactive.bg_fill = CARD;
    v.widgets.inactive.fg_stroke = egui::Stroke::new(1.0, SECONDARY);
    v.widgets.hovered.bg_fill = egui::Color32::from_rgb(13, 21, 32);
    v.widgets.hovered.fg_stroke = egui::Stroke::new(1.0, TEAL);
    v.widgets.active.bg_fill = TEAL;
    v.widgets.active.fg_stroke = egui::Stroke::new(1.0, egui::Color32::BLACK);
    v.selection.bg_fill = egui::Color32::from_rgba_unmultiplied(45, 212, 191, 60);
    v.window_rounding = egui::Rounding::same(12.0);
    ctx.set_visuals(v);
}

fn centered_column(ui: &mut egui::Ui, width: f32, add: impl FnOnce(&mut egui::Ui)) {
    ui.vertical_centered(|ui| {
        ui.set_max_width(width);
        add(ui);
    });
}

fn card(ui: &mut egui::Ui, add: impl FnOnce(&mut egui::Ui)) {
    egui::Frame::none()
        .fill(CARD)
        .rounding(egui::Rounding::same(8.0))
        .inner_margin(egui::Margin::symmetric(16.0, 12.0))
        .stroke(egui::Stroke::new(
            0.667,
            egui::Color32::from_rgba_unmultiplied(45, 212, 191, 30),
        ))
        .show(ui, |ui| {
            ui.set_min_width(420.0);
            add(ui);
        });
}

fn divider(ui: &mut egui::Ui) {
    let (rect, _) = ui.allocate_exact_size(egui::vec2(420.0, 1.0), egui::Sense::hover());
    ui.painter().rect_filled(
        rect,
        egui::Rounding::ZERO,
        egui::Color32::from_rgba_unmultiplied(45, 212, 191, 25),
    );
}

fn bullet(ui: &mut egui::Ui, text: &str) {
    ui.horizontal(|ui| {
        ui.label(egui::RichText::new("▸").color(TEAL).size(12.0));
        ui.label(egui::RichText::new(text).color(SECONDARY).size(12.0));
    });
}

fn field_label(ui: &mut egui::Ui, text: &str) {
    ui.label(
        egui::RichText::new(text)
            .color(MUTED)
            .size(11.0),
    );
    ui.add_space(2.0);
}

fn info_row(ui: &mut egui::Ui, label: &str, value: &str) {
    ui.horizontal(|ui| {
        ui.label(egui::RichText::new(format!("{:<16}", label)).color(MUTED).size(12.0));
        ui.label(egui::RichText::new(value).color(TEXT).size(12.0).monospace());
    });
    ui.add_space(2.0);
}

fn teal_button(ui: &mut egui::Ui, label: &str, width: f32) -> bool {
    let btn = egui::Button::new(
        egui::RichText::new(label)
            .color(egui::Color32::BLACK)
            .strong()
            .size(14.0),
    )
    .fill(TEAL)
    .rounding(egui::Rounding::same(8.0))
    .min_size(egui::vec2(width, 40.0));
    ui.add(btn).clicked()
}

fn outline_button(ui: &mut egui::Ui, label: &str, width: f32) -> bool {
    let btn = egui::Button::new(
        egui::RichText::new(label).color(TEAL).size(14.0),
    )
    .fill(egui::Color32::TRANSPARENT)
    .stroke(egui::Stroke::new(1.0, TEAL))
    .rounding(egui::Rounding::same(8.0))
    .min_size(egui::vec2(width, 40.0));
    ui.add(btn).clicked()
}

fn launch_tray() {
    // Launch the same EXE in --tray mode
    if let Ok(exe) = std::env::current_exe() {
        let _ = std::process::Command::new(&exe).arg("--tray").spawn();
    }
}
