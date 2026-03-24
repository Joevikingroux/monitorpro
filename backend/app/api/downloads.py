import os

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

# Must match the placeholder baked into the base EXE at build time.
# Exactly 64 uppercase X characters — same length as secrets.token_hex(32).
_PLACEHOLDER = b"X" * 64


def _find_base_exe() -> str | None:
    if not os.path.isdir(DOWNLOADS_DIR):
        return None
    exes = sorted(
        (f for f in os.listdir(DOWNLOADS_DIR) if f.endswith(".exe")),
        reverse=True,
    )
    return os.path.join(DOWNLOADS_DIR, exes[0]) if exes else None


@router.post("/build/{company_id}")
async def build_company_probe(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate the company token, patch it into the base EXE by replacing the
    known placeholder bytes, and return the customised EXE for download.

    The client runs the EXE as Administrator — it installs silently with no
    prompts because the token is already baked in.
    """
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    exe_path = _find_base_exe()
    if not exe_path:
        raise HTTPException(
            status_code=404,
            detail="Base EXE not found. Place PCMonitorProbeV1.0.0.exe into the downloads/ folder.",
        )

    # Regenerate company token
    token = generate_api_key()           # 64-char hex string
    company.token_hash = hash_api_key(token)
    db.add(company)
    await db.flush()

    # Binary-patch the placeholder with the real token
    base_bytes = open(exe_path, "rb").read()
    if _PLACEHOLDER not in base_bytes:
        raise HTTPException(
            status_code=500,
            detail="Base EXE does not contain the expected placeholder. Rebuild with COMPANY_TOKEN=XXX...XXX.",
        )

    token_bytes = token.encode("ascii")   # also 64 bytes
    patched = base_bytes.replace(_PLACEHOLDER, token_bytes, 1)

    filename = f"PCMonitorProbe_{company.slug}.exe"
    return StreamingResponse(
        iter([patched]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(patched)),
        },
    )


@router.get("/probe")
async def download_probe():
    """Return the base EXE as-is (no token patching). No auth required."""
    exe_path = _find_base_exe()
    if not exe_path:
        raise HTTPException(
            status_code=404,
            detail="Base EXE not found. Place PCMonitorProbeV*.exe into the downloads/ folder.",
        )

    filename = os.path.basename(exe_path)
    file_size = os.path.getsize(exe_path)

    def iterfile():
        with open(exe_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(file_size),
        },
    )
