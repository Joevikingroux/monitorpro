import io
import os
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, generate_api_key, hash_api_key
from app.models.company import Company
from app.models.user import User

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

DOWNLOADS_DIR = os.environ.get(
    "DOWNLOADS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "downloads"),
)

SERVER_URL = os.environ.get("PUBLIC_URL", "https://monitor.numbers10.co.za")


def _find_base_exe() -> str | None:
    """Return path to the first .exe found in DOWNLOADS_DIR, newest first."""
    if not os.path.isdir(DOWNLOADS_DIR):
        return None
    exes = sorted(
        (f for f in os.listdir(DOWNLOADS_DIR) if f.endswith(".exe")),
        reverse=True,
    )
    if not exes:
        return None
    return os.path.join(DOWNLOADS_DIR, exes[0])


@router.post("/build/{company_id}")
async def build_company_probe(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate the company token, bundle the base probe EXE with the token
    baked in as embedded_token.txt, and return a ready-to-deploy ZIP.

    The client extracts the ZIP, runs PCMonitorProbe_Setup.exe as admin — done.
    """
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    exe_path = _find_base_exe()
    if not exe_path:
        raise HTTPException(
            status_code=404,
            detail=(
                "Base probe EXE not found. Place PCMonitorProbe_Setup.exe "
                "into the downloads/ folder at the repo root."
            ),
        )

    # Regenerate company token — store hash, embed plain text in the package
    token = generate_api_key()
    company.token_hash = hash_api_key(token)
    db.add(company)
    await db.flush()

    config_ini = (
        f"[server]\n"
        f"url = {SERVER_URL}\n"
        f"company_token = {token}\n"
        f"api_key =\n"
        f"ingest_interval_seconds = 30\n"
        f"verify_ssl = true\n"
        f"\n"
        f"[alerts]\n"
        f"local_alert_log = true\n"
        f"\n"
        f"[hardware]\n"
        f"use_open_hardware_monitor = false\n"
    )

    install_txt = (
        f"Numbers10 PCMonitor Probe — {company.name}\n"
        f"{'=' * 50}\n\n"
        f"1. Extract all files to C:\\PCMonitorProbe\\\n"
        f"2. Right-click PCMonitorProbe_Setup.exe\n"
        f"3. Select 'Run as administrator'\n"
        f"4. The probe installs as a Windows Service and starts automatically.\n"
        f"5. This machine will appear in the dashboard under '{company.name}' within 30 seconds.\n\n"
        f"Server: {SERVER_URL}\n"
        f"Company: {company.name}\n"
    )

    # Build ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        zf.write(exe_path, "PCMonitorProbe_Setup.exe")
        zf.writestr("embedded_token.txt", token + "\n")
        zf.writestr("config.ini", config_ini)
        zf.writestr("INSTALL.txt", install_txt)
    zip_bytes = buf.getvalue()

    filename = f"PCMonitorProbe_{company.slug}.zip"
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_bytes)),
        },
    )
