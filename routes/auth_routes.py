from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_session, verify_token
from database.models import User
from schemas import UserScheme, LoginSchema
from main import bcrypt_context, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordRequestForm

auth_router = APIRouter(prefix="/auth", tags=["auth"])

def create_token(id_user, duration=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    expiration_date = datetime.now(timezone.utc) + duration
    dict_info = { "sub": str(id_user), "exp": expiration_date }
    token = jwt.encode(dict_info, SECRET_KEY, ALGORITHM)
    return token

def authenticate_user(email, password, session):
    user = session.query(User).filter(User.email==email).first()
    if not user:
        return False
    elif not bcrypt_context.verify(password, user.password):
        return False
    return user

@auth_router.post("/register")
async def register(user_scheme: UserScheme, session = Depends(get_session)):
    user = session.query(User).filter(User.email == user_scheme.email).first()
    if user:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    else:
        encrypted_password = bcrypt_context.hash(user_scheme.password)
        new_user = User(user_scheme.name, user_scheme.email, encrypted_password)
        session.add(new_user)
        session.commit()
        return { "success" : "User registered successfully" }
    
@auth_router.post("/login")
async def login(login_scheme: LoginSchema, session = Depends(get_session)):
    user = authenticate_user(login_scheme.email, login_scheme.password, session)
    if not user:
        raise HTTPException(status_code=400, detail="User not found or invalid password")
    else:
        access_token = create_token(user.id)
        refresh_token = create_token(user.id, duration=timedelta(days=7))
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type" : "Bearer"
        }

@auth_router.post("/login-form")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session = Depends(get_session)):
    user = authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(status_code=400, detail="User not found or invalid password")
    else:
        access_token = create_token(user.id)
        return {
            "access_token": access_token,
            "token_type" : "Bearer"
        }

@auth_router.get("/refresh")
async def user_refresh_token(user: User = Depends(verify_token)):
    access_token = create_token(user.id)
    return {
            "access_token": access_token,
            "token_type" : "Bearer"
        }