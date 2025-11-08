import os
from fastapi import UploadFile, HTTPException
from PIL import Image

MAX_MB = 5
MAX_BYTES = MAX_MB * 1024 * 1024

def validate_image(upload: UploadFile, max_bytes: int = MAX_BYTES):
    # --- 1️⃣ Check file size ---
    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)

    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (>{MAX_MB} MB)",
        )

    # --- 2️⃣ Check image integrity ---
    try:
        img = Image.open(upload.file)
        img.verify()  # verifies header, doesn’t fully decode
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file")
    finally:
        upload.file.seek(0)  # rewind for next consumer (e.g., S3 upload)