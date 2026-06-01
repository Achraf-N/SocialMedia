from fastapi import APIRouter, Depends, HTTPException, Response, status
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.database import owners_collection
from app.core.dependencies import get_current_owner
from app.core.security import create_access_token, hash_password, verify_password
from app.models.common import now_utc
from app.models.owner_model import AuthResponse, OwnerLogin, OwnerRegister, OwnerResponse
from app.views.serializers import serialize_document

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_payload(owner: dict) -> dict[str, str]:
    return {"owner_id": str(owner["_id"])}


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="none",
        max_age=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=OwnerResponse, status_code=status.HTTP_201_CREATED)
def register(owner_in: OwnerRegister) -> dict:
    now = now_utc()
    owner = {
        "email": owner_in.email,
        "password_hash": hash_password(owner_in.password),
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = owners_collection.insert_one(owner)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An owner with this email already exists",
        ) from exc

    created_owner = owners_collection.find_one({"_id": result.inserted_id})
    return serialize_document(created_owner)


@router.post("/login", response_model=AuthResponse)
def login(credentials: OwnerLogin, response: Response) -> dict:
    owner = owners_collection.find_one({"email": credentials.email})
    if not owner or not verify_password(credentials.password, owner["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(_auth_payload(owner))
    _set_auth_cookie(response, token)

    return {"owner": serialize_document(owner), "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(settings.auth_cookie_name)


@router.get("/me", response_model=OwnerResponse)
def me(owner: dict = Depends(get_current_owner)) -> dict:
    return serialize_document(owner)
