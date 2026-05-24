from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


def _require_supabase_settings() -> None:
    missing = [
        name
        for name, value in {
            "SUPABASE_S3_ENDPOINT": settings.supabase_s3_endpoint,
            "SUPABASE_S3_ACCESS_KEY_ID": settings.supabase_s3_access_key_id,
            "SUPABASE_S3_SECRET_ACCESS_KEY": settings.supabase_s3_secret_access_key,
            "SUPABASE_STORAGE_BUCKET": settings.supabase_storage_bucket,
            "SUPABASE_PUBLIC_URL_BASE": settings.supabase_public_url_base,
        }.items()
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing Supabase storage settings: {', '.join(missing)}",
        )


def _image_extension(filename: str | None, content_type: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix

    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(content_type or "", ".jpg")


def upload_shop_logo(
    *,
    file: UploadFile,
    owner_id: str,
    shop_id: str,
) -> str:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image",
        )

    _require_supabase_settings()

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="boto3 is required for Supabase S3 uploads",
        ) from exc

    extension = _image_extension(file.filename, file.content_type)
    object_key = f"owners/{owner_id}/shops/{shop_id}/logo/{uuid4().hex}{extension}"

    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.supabase_s3_endpoint,
        region_name=settings.supabase_s3_region,
        aws_access_key_id=settings.supabase_s3_access_key_id,
        aws_secret_access_key=settings.supabase_s3_secret_access_key,
    )

    try:
        file.file.seek(0)
        s3_client.upload_fileobj(
            file.file,
            settings.supabase_storage_bucket,
            object_key,
            ExtraArgs={"ContentType": file.content_type},
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload logo to Supabase storage",
        ) from exc

    public_base = settings.supabase_public_url_base.rstrip("/")
    bucket = settings.supabase_storage_bucket.strip("/")
    return f"{public_base}/{bucket}/{object_key}"


def upload_product_image(
    *,
    file: UploadFile,
    owner_id: str,
    shop_id: str,
    product_id: str,
) -> str:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image",
        )

    _require_supabase_settings()

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="boto3 is required for Supabase S3 uploads",
        ) from exc

    extension = _image_extension(file.filename, file.content_type)
    object_key = (
        f"owners/{owner_id}/shops/{shop_id}/products/{product_id}/"
        f"{uuid4().hex}{extension}"
    )

    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.supabase_s3_endpoint,
        region_name=settings.supabase_s3_region,
        aws_access_key_id=settings.supabase_s3_access_key_id,
        aws_secret_access_key=settings.supabase_s3_secret_access_key,
    )

    try:
        file.file.seek(0)
        s3_client.upload_fileobj(
            file.file,
            settings.supabase_storage_bucket,
            object_key,
            ExtraArgs={"ContentType": file.content_type},
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload image to Supabase storage",
        ) from exc

    public_base = settings.supabase_public_url_base.rstrip("/")
    bucket = settings.supabase_storage_bucket.strip("/")
    return f"{public_base}/{bucket}/{object_key}"
