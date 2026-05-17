import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    backend_env = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(backend_env)
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "SocialMedia Backend")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "socialmedia")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-this-secret-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "access_token")
    auth_cookie_secure: bool = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
    supabase_s3_endpoint: str = os.getenv("SUPABASE_S3_ENDPOINT", "")
    supabase_s3_region: str = os.getenv("SUPABASE_S3_REGION", "us-east-1")
    supabase_s3_access_key_id: str = os.getenv("SUPABASE_S3_ACCESS_KEY_ID", "")
    supabase_s3_secret_access_key: str = os.getenv("SUPABASE_S3_SECRET_ACCESS_KEY", "")
    supabase_storage_bucket: str = os.getenv("SUPABASE_STORAGE_BUCKET", "")
    supabase_public_url_base: str = os.getenv("SUPABASE_PUBLIC_URL_BASE", "")


settings = Settings()
