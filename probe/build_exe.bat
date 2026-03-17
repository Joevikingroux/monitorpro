@echo off
REM ============================================================
REM Numbers10 PCMonitor Probe — PyInstaller Build Script
REM Usage:
REM   build_exe.bat                          — Build without embedded token
REM   build_exe.bat COMPANY_TOKEN=abc123     — Build with embedded token
REM ============================================================

setlocal enabledelayedexpansion

set "COMPANY_TOKEN="
set "EXTRA_DATA="

REM Parse COMPANY_TOKEN argument
for %%A in (%*) do (
    for /f "tokens=1,2 delims==" %%B in ("%%A") do (
        if /i "%%B"=="COMPANY_TOKEN" (
            set "COMPANY_TOKEN=%%C"
        )
    )
)

REM If token provided, write to embedded_token.txt
if defined COMPANY_TOKEN (
    echo %COMPANY_TOKEN% > embedded_token.txt
    set "EXTRA_DATA=--add-data embedded_token.txt;."
    echo [BUILD] Embedding company token into EXE
) else (
    echo [BUILD] No company token — probe will use config.ini
)

echo [BUILD] Building PCMonitorProbe_Setup.exe ...

pyinstaller ^
    --onefile ^
    --name PCMonitorProbe_Setup ^
    --icon=NUL ^
    --hidden-import=win32timezone ^
    --hidden-import=collectors.cpu ^
    --hidden-import=collectors.memory ^
    --hidden-import=collectors.disk ^
    --hidden-import=collectors.network ^
    --hidden-import=collectors.processes ^
    --hidden-import=collectors.services ^
    --hidden-import=collectors.event_logs ^
    --hidden-import=collectors.hardware ^
    --hidden-import=collectors.software ^
    --hidden-import=collectors.security ^
    --add-data "config.ini;." ^
    --add-data "collectors;collectors" ^
    %EXTRA_DATA% ^
    probe_agent.py

if %ERRORLEVEL% EQU 0 (
    echo [BUILD] Success! Output: dist\PCMonitorProbe_Setup.exe
    if defined COMPANY_TOKEN (
        del embedded_token.txt 2>NUL
        echo [BUILD] Cleaned up embedded_token.txt
    )
) else (
    echo [BUILD] Build failed!
)

endlocal
