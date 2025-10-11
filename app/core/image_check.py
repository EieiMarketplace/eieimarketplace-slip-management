from PIL import Image
from fastapi import UploadFile, HTTPException

def validate_image(upload: UploadFile):
    try:
        img = Image.open(upload.file)
        img.verify()  # verifies integrity but doesn’t load full image
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file")
    finally:
        upload.file.seek(0)