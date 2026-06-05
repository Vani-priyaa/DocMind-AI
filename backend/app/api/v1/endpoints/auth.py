from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core import security, database
from app.api import deps
from app.models.all_models import User
from app.schemas.user import Token, UserCreate, User as UserSchema

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
def login_access_token(db: Session = Depends(database.get_db), form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=60 * 24 * 8)
    return {
        "access_token": security.create_access_token(user.email, expires_delta=access_token_expires),
        "token_type": "bearer",
    }

@router.post("/register", response_model=UserSchema)
def register_user(user_in: UserCreate, db: Session = Depends(database.get_db)) -> Any:
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(deps.get_current_active_user)):
    return current_user
