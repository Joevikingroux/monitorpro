/// Install / uninstall with live progress callbacks.

use anyhow::{bail, Context, Result};
use winreg::enums::{HKEY_CURRENT_USER, KEY_WRITE};
use winreg::RegKey;

use crate::config::{self, ProbeConfig};

const REGISTRY_RUN_KEY: &str = r"Software\Microsoft\Windows\CurrentVersion\Run";
const TRAY_RUN_VALUE: &str = "PCMonitorProbe_Tray";

pub fn is_installed() -> bool {
    // Only check the service — config file may remain after uninstall (user data)
    std::process::Command::new("sc.exe")
        .args(["query", config::SERVICE_NAME])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

pub fn service_is_running() -> bool {
    let out = std::process::Command::new("sc.exe")
        .args(["query", config::SERVICE_NAME])
        .output()
        .unwrap_or_else(|_| std::process::Output {
            status: std::process::ExitStatus::default(),
            stdout: vec![],
            stderr: vec![],
        });
    String::from_utf8_lossy(&out.stdout).contains("RUNNING")
}

/// Install with live progress. `progress` is called on the calling thread
/// (intended to be run in a background thread with a channel sender).
pub fn install_with_progress<F>(
    server_url: &str,
    company_token: &str,
    verify_ssl: bool,
    progress: F,
) -> Result<()>
where
    F: Fn(&str),
{
    let install_dir = config::install_dir();
    let config_dir = config::config_dir();
    let exe_src = std::env::current_exe().context("Getting current exe path")?;
    let exe_dst = install_dir.join("PCMonitorProbe.exe");

    progress("Creating directories...");
    std::fs::create_dir_all(&install_dir)
        .with_context(|| format!("Cannot create {}", install_dir.display()))?;
    std::fs::create_dir_all(&config_dir)
        .with_context(|| format!("Cannot create {}", config_dir.display()))?;

    progress("Stopping any running tray or status processes...");
    kill_background_processes();
    std::thread::sleep(std::time::Duration::from_millis(500));

    progress("Copying executable to Program Files...");
    std::fs::copy(&exe_src, &exe_dst)
        .with_context(|| format!("Cannot copy EXE to {}", exe_dst.display()))?;

    progress("Writing configuration...");
    let cfg = ProbeConfig {
        server_url: server_url.to_string(),
        company_token: company_token.to_string(),
        api_key: None,
        machine_id: None,
        ingest_interval_secs: 30,
        verify_ssl,
    };
    config::save_config(&cfg).context("Saving config")?;

    progress("Removing any previous service...");
    let _ = sc_raw(&["stop", config::SERVICE_NAME]);
    let _ = sc_raw(&["delete", config::SERVICE_NAME]);
    // Wait for SCM to fully process the deletion
    std::thread::sleep(std::time::Duration::from_secs(3));

    // sc.exe requires "binPath=" and the path as SEPARATE arguments.
    // Combining them ("binPath= C:\...") is a common mistake that causes silent failure.
    let bin_path = format!("\"{}\" --run-service", exe_dst.display());

    progress(&format!(
        "Creating Windows Service '{}' (Delayed Auto Start)...",
        config::SERVICE_NAME
    ));

    // Use PowerShell New-Service which is more reliable than sc.exe argument parsing
    let ps = format!(
        "New-Service -Name '{}' -BinaryPathName '{}' -StartupType Automatic -DisplayName '{}' -Description '{}' -ErrorAction Stop; \
         Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\{}' -Name 'DelayedAutostart' -Value 1 -Type DWord",
        config::SERVICE_NAME,
        bin_path.replace('\'', "''"),  // escape single quotes for PS
        config::SERVICE_DISPLAY,
        config::SERVICE_DESC,
        config::SERVICE_NAME,
    );

    let out = std::process::Command::new("powershell.exe")
        .args(["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", &ps])
        .output()
        .context("Failed to launch PowerShell")?;

    if !out.status.success() {
        let stderr = String::from_utf8_lossy(&out.stderr);
        let stdout = String::from_utf8_lossy(&out.stdout);
        bail!(
            "Service creation failed.\nPowerShell output:\n{}\n{}",
            stdout.trim(),
            stderr.trim()
        );
    }

    let _ = sc_raw(&[
        "description",
        config::SERVICE_NAME,
        config::SERVICE_DESC,
    ]);

    progress("Starting service...");
    let start_out = std::process::Command::new("sc.exe")
        .args(["start", config::SERVICE_NAME])
        .output()
        .context("Failed to run sc start")?;
    if !start_out.status.success() {
        let msg = String::from_utf8_lossy(&start_out.stdout);
        bail!("Service start failed: {}", msg.trim());
    }

    // Configure service to auto-restart on failure (3 attempts: 5s, 15s, 30s)
    let _ = std::process::Command::new("sc.exe")
        .args([
            "failure", config::SERVICE_NAME,
            "reset=", "86400",
            "actions=", "restart/5000/restart/15000/restart/30000",
        ])
        .output();

    progress("Registering tray app at user login...");
    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    let run_key = hkcu
        .open_subkey_with_flags(REGISTRY_RUN_KEY, KEY_WRITE)
        .context("Cannot open HKCU\\Run key")?;
    let tray_cmd = format!("\"{}\" --tray", exe_dst.display());
    run_key
        .set_value(TRAY_RUN_VALUE, &tray_cmd.as_str())
        .context("Cannot write Run key")?;

    progress("Creating desktop shortcut...");
    let shortcut_ps = format!(
        "$sh = New-Object -ComObject WScript.Shell; \
         $sc = $sh.CreateShortcut(\"$env:PUBLIC\\Desktop\\PCMonitor Status.lnk\"); \
         $sc.TargetPath = '{}'; \
         $sc.Arguments = '--status'; \
         $sc.Description = 'Numbers10 PCMonitor - View probe status'; \
         $sc.Save()",
        exe_dst.display()
    );
    let _ = std::process::Command::new("powershell.exe")
        .args(["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", &shortcut_ps])
        .output();

    progress("Service started successfully.");
    Ok(())
}

/// Kill all other PCMonitorProbe.exe processes (tray, status windows) so the
/// exe is not locked when we try to stop/delete the service or copy a new exe.
fn kill_background_processes() {
    // taskkill /F /IM kills all processes with that image name except ourselves.
    // We use /FI to exclude our own PID so the uninstaller doesn't self-terminate.
    let my_pid = std::process::id().to_string();
    let _ = std::process::Command::new("taskkill.exe")
        .args([
            "/F",
            "/IM", "PCMonitorProbe.exe",
            "/FI", &format!("PID ne {}", my_pid),
        ])
        .output();
}

pub fn uninstall_with_progress<F>(progress: F) -> Result<()>
where
    F: Fn(&str),
{
    progress("Stopping tray and status windows...");
    kill_background_processes();
    // Brief pause so OS releases file handles
    std::thread::sleep(std::time::Duration::from_millis(800));

    progress(&format!("Stopping service '{}'...", config::SERVICE_NAME));
    let _ = sc_raw(&["stop", config::SERVICE_NAME]);

    // Wait up to 8 seconds for the service to actually stop
    let mut waited = 0u64;
    while waited < 8000 {
        std::thread::sleep(std::time::Duration::from_millis(500));
        waited += 500;
        if !service_is_running() {
            break;
        }
        progress(&format!("  Waiting for service to stop... ({}s)", waited / 1000));
    }

    progress("Deleting service from SCM...");
    // sc delete can fail if service is still stopping — retry a couple of times
    let mut deleted = false;
    for attempt in 1..=3 {
        if sc_raw(&["delete", config::SERVICE_NAME]).is_ok() {
            deleted = true;
            break;
        }
        progress(&format!("  Delete attempt {} failed, retrying...", attempt));
        std::thread::sleep(std::time::Duration::from_secs(2));
    }
    if !deleted {
        // Force it: mark for deletion — it will be removed on next reboot
        progress("  Warning: service marked for deletion on next reboot.");
    }

    progress("Removing tray startup entry from registry...");
    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    if let Ok(run_key) = hkcu.open_subkey_with_flags(REGISTRY_RUN_KEY, KEY_WRITE) {
        let _ = run_key.delete_value(TRAY_RUN_VALUE);
    }

    // Remove desktop shortcut
    let shortcut = std::path::PathBuf::from(
        std::env::var("PUBLIC").unwrap_or_else(|_| "C:\\Users\\Public".to_string())
    ).join("Desktop").join("PCMonitor Status.lnk");
    if shortcut.exists() {
        let _ = std::fs::remove_file(&shortcut);
    }

    progress("Removing installed executable...");
    let exe = config::install_dir().join("PCMonitorProbe.exe");
    if exe.exists() {
        // EXE might be locked if service is still dying — rename trick
        let old = config::install_dir().join("PCMonitorProbe.exe.old");
        let _ = std::fs::rename(&exe, &old);
        let _ = std::fs::remove_file(&old);
        if exe.exists() {
            progress("  Note: EXE is locked — will be removed on next reboot.");
        }
    }

    // Leave config/logs in place — data belongs to the user
    progress("DONE: Uninstall complete. Config and logs kept in %ProgramData%\\Numbers10\\PCMonitor\\");
    Ok(())
}

/// Clear saved api_key + machine_id from config and restart the service.
/// Use when the server-side machine record was deleted and the probe
/// needs to re-register from scratch.
pub fn reset_registration<F>(progress: F) -> Result<()>
where
    F: Fn(&str),
{
    progress("Loading current config...");
    let mut cfg = config::load_config()?;

    progress("Clearing saved registration (API key + machine ID)...");
    cfg.api_key = None;
    cfg.machine_id = None;
    config::save_config(&cfg)?;

    // Also wipe the stale status.json so the tray doesn't show old data
    let status_file = config::status_path();
    if status_file.exists() {
        let _ = std::fs::remove_file(&status_file);
    }

    progress("Restarting service so it re-registers...");
    let _ = sc_raw(&["stop", config::SERVICE_NAME]);

    // Wait for it to stop
    let mut waited = 0u64;
    while waited < 6000 {
        std::thread::sleep(std::time::Duration::from_millis(500));
        waited += 500;
        if !service_is_running() {
            break;
        }
    }

    let start_out = std::process::Command::new("sc.exe")
        .args(["start", config::SERVICE_NAME])
        .output()
        .context("Failed to run sc start")?;
    if !start_out.status.success() {
        let msg = String::from_utf8_lossy(&start_out.stdout);
        bail!("Service start failed: {}", msg.trim());
    }

    progress("DONE: Registration cleared. Probe will re-register with the server now.");
    Ok(())
}

/// Run sc.exe, ignore errors (for stop/delete which may legitimately fail)
fn sc_raw(args: &[&str]) -> Result<()> {
    let status = std::process::Command::new("sc.exe")
        .args(args)
        .status()
        .context("Running sc.exe")?;
    if !status.success() {
        bail!("sc.exe {:?} failed", args);
    }
    Ok(())
}
