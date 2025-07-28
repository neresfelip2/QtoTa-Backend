from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_session, verify_token
from database.models import User
from schemas import UserScheme, LoginSchema
from main import bcrypt_context
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from repository.auth_repository import get_user, create_token

auth_router = APIRouter(prefix="/auth", tags=["auth"])

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
        access_token = create_token(new_user.id)
        refresh_token = create_token(new_user.id, duration=timedelta(days=7))
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type" : "Bearer"
        }
    
@auth_router.post("/login")
async def login(login_scheme: LoginSchema, session = Depends(get_session)):
    user = get_user(login_scheme.email, session)
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não cadastrado")
    elif not bcrypt_context.verify(login_scheme.password, user.password):
        raise HTTPException(status_code=400, detail="Senha inválida")
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
    user = get_user(form_data.username, session)
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não cadastrado")
    elif not bcrypt_context.verify(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Senha inválida")
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