import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

# Place PCMonitorProbe_Setup.exe in the downloads/ folder at the repo root
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "downloads")


@router.get("/probe")
async def download_probe():
    """Stream PCMonitorProbe_Setup.exe from the downloads/ directory."""
    # Find any .exe in the downloads dir (picks up versioned filenames too)
    exe_path = None
    if os.path.isdir(DOWNLOADS_DIR):
        for name in sorted(os.listdir(DOWNLOADS_DIR), reverse=True):
            if name.endswith(".exe"):
                exe_path = os.path.join(DOWNLOADS_DIR, name)
                break

    if not exe_path or not os.path.isfile(exe_path):
        raise HTTPException(
            status_code=404,
            detail=(
                "Probe installer not found. Build it with probe/build_exe.bat "
                "then place the .exe into the downloads/ folder at the repo root."
            ),
        )

    file_size = os.path.getsize(exe_path)
    filename = os.path.basename(exe_path)

    def iter_file():
        with open(exe_path, "rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    return StreamingResponse(
        iter_file(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(file_size),
        },
    )
