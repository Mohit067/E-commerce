"""Error envelope + auth + users + addresses."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ... import models
from ...config import get_settings
from ...database import get_db
from ...deps import get_current_user, require_roles
from ...schemas import AddressIn, AddressOut, LoginIn, ProfileUpdateIn, RefreshIn, SignupIn, TokenOut, UserOut
from ...security import create_access_token, create_refresh_token, decode_refresh_token, hash_password, verify_password

settings = get_settings()
router = APIRouter()


def _out(u: models.User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role,
            "is_active": u.is_active, "avatar_url": u.avatar_url, "phone": u.phone,
            "created_at": u.created_at}


@router.post("/signup", response_model=TokenOut, summary="Create account")
def signup(data: SignupIn, db: Session = Depends(get_db)):
    if db.query(models.User).filter_by(email=data.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    u = models.User(email=data.email.lower(), password_hash=hash_password(data.password),
                    full_name=data.full_name, role="customer")
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"access_token": create_access_token(u.id, u.role),
            "refresh_token": create_refresh_token(u.id), "token_type": "bearer"}


@router.post("/login", response_model=TokenOut, summary="Login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    u = db.query(models.User).filter_by(email=data.email.lower()).first()
    if not u or not verify_password(data.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not u.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return {"access_token": create_access_token(u.id, u.role),
            "refresh_token": create_refresh_token(u.id), "token_type": "bearer"}


@router.post("/refresh", response_model=TokenOut, summary="Refresh tokens")
def refresh(data: RefreshIn, db: Session = Depends(get_db)):
    try:
        payload = decode_refresh_token(data.refresh_token)
        u = db.get(models.User, payload.get("sub", ""))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if not u or not u.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return {"access_token": create_access_token(u.id, u.role),
            "refresh_token": create_refresh_token(u.id), "token_type": "bearer"}


@router.post("/logout", summary="Logout (client discards tokens)")
def logout():
    return {"ok": True}


@router.get("/me", response_model=UserOut, summary="Current profile")
def me(user: models.User = Depends(get_current_user)):
    return _out(user)


@router.patch("/me", response_model=UserOut, summary="Update profile")
def update_me(data: ProfileUpdateIn, db: Session = Depends(get_db),
              user: models.User = Depends(get_current_user)):
    u = db.get(models.User, user.id)
    if data.full_name is not None:
        u.full_name = data.full_name
    if data.phone is not None:
        u.phone = data.phone
    if data.avatar_url is not None:
        u.avatar_url = data.avatar_url
    db.commit()
    db.refresh(u)
    return _out(u)


users_router = APIRouter()


@users_router.get("/me/addresses", response_model=list[AddressOut])
def my_addresses(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return [{"id": a.id, "user_id": a.user_id, "label": a.label, "full_name": a.full_name,
             "line1": a.line1, "line2": a.line2, "city": a.city, "state": a.state,
             "postal_code": a.postal_code, "country": a.country, "phone": a.phone,
             "is_default": a.is_default} for a in db.query(models.Address).filter_by(user_id=user.id).all()]


@users_router.post("/me/addresses", response_model=AddressOut, status_code=201)
def add_address(data: AddressIn, db: Session = Depends(get_db),
                user: models.User = Depends(get_current_user)):
    if data.is_default:
        db.query(models.Address).filter_by(user_id=user.id).update({"is_default": False})
    a = models.Address(user_id=user.id, **data.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id, "user_id": a.user_id, **data.model_dump()}


@users_router.get("", response_model=list[UserOut], summary="List users (admin)")
def list_users(db: Session = Depends(get_db), admin: models.User = Depends(require_roles("admin", "manager"))):
    return [_out(u) for u in db.query(models.User).order_by(models.User.created_at.desc()).limit(200).all()]
