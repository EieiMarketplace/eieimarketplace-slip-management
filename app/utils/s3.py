from aiohttp import ClientError
from fastapi import HTTPException
import boto3
from app.core.config import settings
from botocore.exceptions import NoCredentialsError

S3_BUCKET_NAME = settings.S3_BUCKET_NAME

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.REGION_NAME,
)
print("AWS_ACCESS_KEY_ID =", settings.AWS_ACCESS_KEY_ID)
print("AWS_SECRET_ACCESS_KEY =", settings.AWS_SECRET_ACCESS_KEY)
print("REGION_NAME =", settings.REGION_NAME)
print("S3_BUCKET_NAME =", S3_BUCKET_NAME)

def upload_file_to_s3(file_obj, filename: str, content_type: str = None) -> str:
    """
    อัปโหลดไฟล์ไป S3
    
    Args:
        file_obj: The file object to upload
        filename: The key/name to use in S3
        content_type: The content type of the file (e.g., 'image/png')
    
    Returns:
        str: The key used in S3 (not the full URL)
    """
    try:
        extra_args = {"ContentType": content_type} if content_type else {}
        s3_client.upload_fileobj(file_obj, S3_BUCKET_NAME, filename, ExtraArgs=extra_args)
        # Return only the key, not the full URL
        return filename
    except NoCredentialsError:
        raise RuntimeError("AWS credentials not found.")
    except Exception as e:
        raise RuntimeError(f"Failed to upload file: {e}")
    
def get_presigned_url(filename: str, expires_in: int = 3600) -> str:
    """
    คืน URL สำหรับ GET ไฟล์จาก S3 (private bucket)
    expires_in: วินาทีที่ URL ใช้งานได้
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": filename},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as e:
        raise RuntimeError(f"Failed to generate presigned URL: {e}")
        
# Alias for get_presigned_url to match function name in router.py
generate_presigned_url = get_presigned_url
    
def delete_with_image_key(imageKey:str):
    """
        Delete Image from S3 with Image Key
    """
    try:
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=imageKey)
        return {"message": f"Image '{imageKey}' deleted successfully from S3 bucket '{S3_BUCKET_NAME}'."}
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(status_code=404, detail=f"Image '{imageKey}' not found in S3 bucket '{S3_BUCKET_NAME}'.")
        else:
            raise HTTPException(status_code=500, detail=f"Error deleting image from S3: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

def validate_images_exist(key: list[str]):
    """
    ตรวจสอบว่า image_keys มีอยู่ใน S3
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=key)  
        return True   
    except ClientError as e:
        if e.response['Error']['Code'] == '404' or e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(
                status_code=404,
                detail=f"Image '{key}' not found in S3 bucket '{S3_BUCKET_NAME}'."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error checking image '{key}' in S3: {e}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
  