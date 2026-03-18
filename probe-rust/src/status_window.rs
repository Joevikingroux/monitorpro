/// Standalone status window — launched as a subprocess with --status flag.
/// Runs a normal visible eframe window. Exits the process when the user
/// closes it. Can be opened and closed any number of times cleanly.

use eframe::egui;
use image::RgbaImage;

use crate::ipc::{self, ProbeStatus};
use crate::config;

static LOGO_BYTES: &[u8] = include_bytes!("../assets/logo.png");

const BG_BLACK:    egui::Color32 = egui::Color32::from_rgb(0, 0, 0);
const BG_SURFACE:  egui::Color32 = egui::Color32::from_rgb(5, 10, 18);
const BG_CARD:     egui::Color32 = egui::Color32::from_rgb(10, 18, 32);
const TEXT_PRIMARY: egui::Color32 = egui::Color32::from_rgb(224, 247, 250);
const TEXT_MUTED:  egui::Color32 = egui::Color32::from_rgb(100, 116, 139);
const ACCENT:      egui::Color32 = egui::Color32::from_rgb(45, 212, 191);
const STATUS_RED:  egui::Color32 = egui::Color32::from_rgb(239, 68, 68);
const STATUS_AMBER: egui::Color32 = egui::Color32::from_rgb(245, 158, 11);

struct StatusApp {
    status: ProbeStatus,
    pulse_t: f32,
    last_read: std::time::Instant,
    logo_tex: Option<egui::TextureHandle>,
    logo_aspect: f32,
}

impl StatusApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        apply_theme(&cc.egui_ctx);
        let (logo_tex, logo_aspect) = load_logo(&cc.egui_ctx);
        let status = ipc::read_status().unwrap_or_default();
        Self {
            status,
            pulse_t: 0.0,
            last_read: std::time::Instant::now(),
            logo_tex,
            logo_aspect,
        }
    }
}

impl eframe::App for StatusApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Refresh status every 3 seconds
        if self.last_read.elapsed().as_secs() >= 3 {
            self.last_read = std::time::Instant::now();
            if let Some(s) = ipc::read_status() {
                self.status = s;
            }
        }

        self.pulse_t += ctx.input(|i| i.stable_dt);

        egui::CentralPanel::default()
            .frame(egui::Frame::none().fill(BG_BLACK))
            .show(ctx, |ui| {
                ui.add_space(16.0);

                // ── Header ─────────────────────────────────────────────
                ui.vertical_centered(|ui| {
                    if let Some(tex) = &self.logo_tex {
                        let w = 140.0f32;
                        let h = w * self.logo_aspect;
                        ui.add(egui::Image::from_texture(egui::load::SizedTexture::new(
                            tex.id(),
                            egui::vec2(w, h),
                        )));
                    } else {
                        ui.label(
                            egui::RichText::new("◆ Numbers10")
                                .color(ACCENT)
                                .size(22.0)
                                .strong(),
                        );
                    }
                    ui.add_space(4.0);
                    ui.label(
                        egui::RichText::new("PCMonitor Probe Status")
                            .color(egui::Color32::from_rgb(148, 163, 184))
                            .size(13.0),
                    );
                });

                ui.add_space(12.0);
                let (r, _) = ui.allocate_exact_size(
                    egui::vec2(ui.available_width(), 1.0),
                    egui::Sense::hover(),
                );
                ui.painter().rect_filled(
                    r,
                    egui::Rounding::ZERO,
                    egui::Color32::from_rgba_unmultiplied(45, 212, 191, 30),
                );
                ui.add_space(10.0);

                // ── Connection card ─────────────────────────────────────
                margin_card(ui, |ui| {
                    ui.horizontal(|ui| {
                        let alpha =
                            ((self.pulse_t * 2.5).sin() * 0.35 + 0.65).clamp(0.3, 1.0);
                        let dot_color = if self.status.connected {
                            egui::Color32::from_rgba_unmultiplied(
                                45, 212, 191, (alpha * 255.0) as u8,
                            )
                        } else {
                            STATUS_RED
                        };
                        let (r, _) = ui.allocate_exact_size(
                            egui::vec2(10.0, 10.0),
                            egui::Sense::hover(),
                        );
                        ui.painter().circle_filled(r.center(), 5.0, dot_color);
                        ui.add_space(6.0);

                        let (txt, col) = if self.status.connected {
                            ("Connected", ACCENT)
                        } else {
                            ("Disconnected", STATUS_RED)
                        };
                        ui.label(
                            egui::RichText::new(txt).color(col).strong().size(14.0),
                        );

                        if let Some(ms) = self.status.latency_ms {
                            ui.with_layout(
                                egui::Layout::right_to_left(egui::Align::Center),
                                |ui| {
                                    let lc = if ms < 100 {
                                        ACCENT
                                    } else if ms < 500 {
                                        STATUS_AMBER
                                    } else {
                                        STATUS_RED
                                    };
                                    ui.label(
                                        egui::RichText::new(format!("{} ms", ms))
                                            .color(lc)
                                            .monospace()
                                            .size(13.0),
                                    );
                                },
                            );
                        }
                    });
                });

                // ── Info card ───────────────────────────────────────────
                margin_card(ui, |ui| {
                    stat_row(ui, "Server", &self.status.server_url);
                    stat_row(ui, "Company Token", &self.status.company_token_hint);
                    stat_row(
                        ui,
                        "Machine ID",
                        self.status
                            .machine_id
                            .as_deref()
                            .unwrap_or("Pending registration…"),
                    );
                    stat_row(
                        ui,
                        "Last Upload",
                        &self
                            .status
                            .last_metric_sent
                            .map(|t| t.format("%Y-%m-%d %H:%M:%S UTC").to_string())
                            .unwrap_or_else(|| "Never".to_string()),
                    );
                    stat_row(ui, "Agent Version", &self.status.service_version);
                });

                // ── Metric bars ─────────────────────────────────────────
                margin_card(ui, |ui| {
                    metric_bar(ui, "CPU", self.status.cpu_percent);
                    ui.add_space(6.0);
                    metric_bar(ui, "RAM", self.status.ram_percent);
                    ui.add_space(6.0);
                    metric_bar(ui, "Disk", self.status.disk_percent);
                });

                // ── Error ───────────────────────────────────────────────
                if let Some(err) = &self.status.error_message.clone() {
                    ui.add_space(4.0);
                    egui::Frame::none()
                        .fill(egui::Color32::from_rgba_unmultiplied(239, 68, 68, 18))
                        .rounding(egui::Rounding::same(6.0))
                        .inner_margin(egui::Margin::symmetric(14.0, 8.0))
                        .outer_margin(egui::Margin::symmetric(16.0, 0.0))
                        .show(ui, |ui| {
                            ui.label(
                                egui::RichText::new(format!("⚠  {}", err))
                                    .color(STATUS_RED)
                                    .size(11.0),
                            );
                        });
                }

                ui.add_space(10.0);

                // ── Close button — exits the process ────────────────────
                ui.vertical_centered(|ui| {
                    let btn = egui::Button::new(
                        egui::RichText::new("  Close  ")
                            .color(egui::Color32::BLACK)
                            .strong(),
                    )
                    .fill(ACCENT)
                    .rounding(egui::Rounding::same(6.0))
                    .min_size(egui::vec2(120.0, 32.0));
                    if ui.add(btn).clicked() {
                        std::process::exit(0);
                    }
                });

                ui.add_space(12.0);
            });

        ctx.request_repaint_after(std::time::Duration::from_millis(500));
    }
}

// ── Entry point ───────────────────────────────────────────────────────────

pub fn run() {
    let opts = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("Numbers10 PCMonitor - Status")
            .with_inner_size([460.0, 490.0])
            .with_min_inner_size([420.0, 420.0])
            .with_resizable(false)
            .with_visible(true),
        centered: true,
        ..Default::default()
    };

    eframe::run_native(
        "Numbers10 PCMonitor - Status",
        opts,
        Box::new(|cc| Box::new(StatusApp::new(cc))),
    )
    .ok();
}

// ── Helpers ───────────────────────────────────────────────────────────────

fn margin_card(ui: &mut egui::Ui, add: impl FnOnce(&mut egui::Ui)) {
    egui::Frame::none()
        .fill(BG_CARD)
        .rounding(egui::Rounding::same(8.0))
        .inner_margin(egui::Margin::symmetric(14.0, 10.0))
        .outer_margin(egui::Margin::symmetric(14.0, 4.0))
        .stroke(egui::Stroke::new(
            0.667,
            egui::Color32::from_rgba_unmultiplied(45, 212, 191, 25),
        ))
        .show(ui, |ui| add(ui));
}

fn stat_row(ui: &mut egui::Ui, label: &str, value: &str) {
    ui.horizontal(|ui| {
        ui.label(
            egui::RichText::new(format!("{:<18}", label))
                .color(TEXT_MUTED)
                .size(12.0),
        );
        ui.label(
            egui::RichText::new(value)
                .color(TEXT_PRIMARY)
                .size(12.0)
                .monospace(),
        );
    });
    ui.add_space(2.0);
}

fn metric_bar(ui: &mut egui::Ui, label: &str, pct: f32) {
    ui.horizontal(|ui| {
        ui.label(
            egui::RichText::new(format!("{:<6}", label))
                .color(egui::Color32::from_rgb(148, 163, 184))
                .size(12.0),
        );
        ui.add_space(6.0);

        let color = if pct < 60.0 {
            ACCENT
        } else if pct < 80.0 {
            STATUS_AMBER
        } else {
            STATUS_RED
        };
        let avail = (ui.available_width() - 50.0).max(60.0);
        let (rect, _) =
            ui.allocate_exact_size(egui::vec2(avail, 10.0), egui::Sense::hover());

        ui.painter().rect_filled(
            rect,
            egui::Rounding::same(3.0),
            egui::Color32::from_rgb(13, 21, 32),
        );
        let fw = rect.width() * (pct / 100.0).clamp(0.0, 1.0);
        if fw > 0.0 {
            let fr =
                egui::Rect::from_min_size(rect.min, egui::vec2(fw, rect.height()));
            ui.painter()
                .rect_filled(fr, egui::Rounding::same(3.0), color);
        }

        ui.add_space(6.0);
        ui.label(
            egui::RichText::new(format!("{:.0}%", pct))
                .color(color)
                .monospace()
                .size(12.0),
        );
    });
}

fn apply_theme(ctx: &egui::Context) {
    let mut v = egui::Visuals::dark();
    v.panel_fill = BG_BLACK;
    v.window_fill = BG_SURFACE;
    v.faint_bg_color = BG_CARD;
    v.extreme_bg_color = BG_BLACK;
    v.window_stroke = egui::Stroke::new(
        0.667,
        egui::Color32::from_rgba_unmultiplied(45, 212, 191, 38),
    );
    v.widgets.noninteractive.fg_stroke = egui::Stroke::new(1.0, egui::Color32::from_rgb(148, 163, 184));
    v.widgets.hovered.fg_stroke = egui::Stroke::new(1.0, ACCENT);
    v.window_rounding = egui::Rounding::same(12.0);
    ctx.set_visuals(v);
}

fn load_logo(ctx: &egui::Context) -> (Option<egui::TextureHandle>, f32) {
    match image::load_from_memory(LOGO_BYTES) {
        Ok(img) => {
            let rgba = img.to_rgba8();
            let (w, h) = (rgba.width() as usize, rgba.height() as usize);
            let aspect = h as f32 / w as f32;
            let tex = ctx.load_texture(
                "logo",
                egui::ColorImage::from_rgba_unmultiplied([w, h], &rgba.into_raw()),
                egui::TextureOptions::LINEAR,
            );
            (Some(tex), aspect)
        }
        Err(_) => (None, 0.3),
    }
}
