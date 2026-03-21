fn main() {
    // Embed icon and version info into the Windows EXE
    #[cfg(windows)]
    {
        let mut res = winres::WindowsResource::new();
        res.set_icon("assets/logo.ico");
        res.set("FileDescription", "Numbers10 PCMonitor Probe");
        res.set("ProductName", "PCMonitor Probe");
        res.set("CompanyName", "Numbers10 Technology Solutions");
        res.set("LegalCopyright", "\u{00A9} 2025 Numbers10 Technology Solutions");
        res.set("FileVersion", "1.0.0.0");
        res.set("ProductVersion", "1.0.0.0");
        // Mark as Windows GUI app (no console flash on double-click)
        res.set_manifest(r#"
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
    </application>
  </compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/PM</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
    </windowsSettings>
  </application>
</assembly>
"#);
        if let Err(e) = res.compile() {
            // Don't fail the build if icon is missing during dev
            eprintln!("cargo:warning=winres compile warning: {}", e);
        }
    }

    // Re-run if env vars change (baked-in server/company at build time)
    println!("cargo:rerun-if-env-changed=SERVER_URL");
    println!("cargo:rerun-if-env-changed=COMPANY_TOKEN");
    println!("cargo:rerun-if-changed=assets/logo.ico");
    println!("cargo:rerun-if-changed=assets/logo.png");
}
