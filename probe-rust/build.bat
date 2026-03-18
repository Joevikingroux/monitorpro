@echo off
setlocal EnableDelayedExpansion

:: ============================================================
::  Numbers10 PCMonitor — Rust Probe Build Script
::
::  Usage:
::    build.bat                              (dev build, no baked token)
::    build.bat <SERVER_URL> <COMPANY_TOKEN> (bake token into exe)
::
::  Examples:
::    build.bat https://monitor.numbers10.co.za:8443 abc123xyz456
::
::  Output: dist\PCMonitorProbe.exe
:: ============================================================

set SERVER_URL=%1
set COMPANY_TOKEN=%2

echo.
echo  Numbers10 PCMonitor — Probe Builder
echo  =====================================

:: Check Rust is installed
where cargo >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Rust/Cargo not found.
    echo  Install from: https://rustup.rs
    pause
    exit /b 1
)

:: Convert logo.png to .ico if not already done
if not exist "assets\logo.ico" (
    if exist "assets\logo.png" (
        echo  Converting logo.png to logo.ico...
        :: Use PowerShell + System.Drawing to convert PNG->ICO
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
            "$src = 'assets\logo.png'; $dst = 'assets\logo.ico';" ^
            "Add-Type -AssemblyName System.Drawing;" ^
            "$bmp = [System.Drawing.Bitmap]::new($src);" ^
            "$sizes = @(16,32,48,64,128,256);" ^
            "$ms = New-Object System.IO.MemoryStream;" ^
            "$bw = New-Object System.IO.BinaryWriter($ms);" ^
            "$bw.Write([byte]0); $bw.Write([byte]0);" ^
            "$bw.Write([uint16]1); $bw.Write([uint16]$sizes.Count);" ^
            "$offset = 6 + $sizes.Count * 16;" ^
            "$images = @();" ^
            "foreach ($s in $sizes) {" ^
            "  $resized = New-Object System.Drawing.Bitmap($bmp, $s, $s);" ^
            "  $imgMs = New-Object System.IO.MemoryStream;" ^
            "  $resized.Save($imgMs, [System.Drawing.Imaging.ImageFormat]::Png);" ^
            "  $images += $imgMs.ToArray();" ^
            "  $bw.Write([byte]$(if($s -eq 256){0}else{$s})); $bw.Write([byte]$(if($s -eq 256){0}else{$s}));" ^
            "  $bw.Write([byte]0); $bw.Write([byte]0);" ^
            "  $bw.Write([uint16]1); $bw.Write([uint16]32);" ^
            "  $bw.Write([uint32]$images[-1].Length); $bw.Write([uint32]$offset);" ^
            "  $offset += $images[-1].Length;" ^
            "};" ^
            "foreach ($img in $images) { $bw.Write($img) };" ^
            "$bw.Flush(); [System.IO.File]::WriteAllBytes($dst, $ms.ToArray());" ^
            "Write-Host '  logo.ico created.'"
    ) else (
        echo  WARNING: assets\logo.png not found — no icon will be embedded.
    )
)

:: Copy logo to assets if it exists in frontend
if not exist "assets\logo.png" (
    if exist "..\frontend\public\logo.png" (
        copy "..\frontend\public\logo.png" "assets\logo.png" >nul
        echo  Copied logo.png from frontend\public\
    )
)

if "%SERVER_URL%"=="" (
    echo  Building without baked-in server/company ^(dev mode^)...
    cargo build --release
) else (
    if "%COMPANY_TOKEN%"=="" (
        echo  ERROR: COMPANY_TOKEN required when SERVER_URL is specified.
        echo  Usage: build.bat ^<SERVER_URL^> ^<COMPANY_TOKEN^>
        pause
        exit /b 1
    )
    echo  Building with baked-in config:
    echo    Server  : %SERVER_URL%
    echo    Company : %COMPANY_TOKEN:~0,8%...
    set SERVER_URL=%SERVER_URL%
    set COMPANY_TOKEN=%COMPANY_TOKEN%
    cargo build --release
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  BUILD FAILED — check errors above.
    pause
    exit /b 1
)

:: Copy to dist/
if not exist "dist" mkdir dist
copy /Y "target\x86_64-pc-windows-msvc\release\PCMonitorProbe.exe" "dist\PCMonitorProbe.exe" >nul 2>&1
:: Fallback for non-MSVC toolchain
if %ERRORLEVEL% NEQ 0 (
    copy /Y "target\release\PCMonitorProbe.exe" "dist\PCMonitorProbe.exe" >nul
)

:: If company token provided, also create a named copy for identification
if not "%COMPANY_TOKEN%"=="" (
    set TOKEN_SHORT=%COMPANY_TOKEN:~0,8%
    copy /Y "dist\PCMonitorProbe.exe" "dist\PCMonitorProbe_%TOKEN_SHORT%.exe" >nul
    echo.
    echo  ============================================================
    echo   Build complete!
    echo   EXE: dist\PCMonitorProbe_%TOKEN_SHORT%.exe
    echo.
    echo   Deploy to client PC:
    echo   1. Copy dist\PCMonitorProbe_%TOKEN_SHORT%.exe to the PC
    echo   2. Right-click ^> Run as Administrator
    echo   3. It will auto-install, connect to %SERVER_URL%
    echo   4. Machine appears in dashboard under the company
    echo  ============================================================
) else (
    echo.
    echo  ============================================================
    echo   Dev build complete: dist\PCMonitorProbe.exe
    echo.
    echo   To install:
    echo   PCMonitorProbe.exe install --server ^<URL^> --company ^<TOKEN^>
    echo  ============================================================
)

echo.
pause
