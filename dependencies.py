from fastapi import Depends, HTTPException
from database import engine
from sqlalchemy.orm import sessionmaker
from models import User
from main import SECRET_KEY, ALGORITHM, oauth2_schema
from jose import jwt, JWTError

def get_session():
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
    finally:
        session.close()

def verify_token(token: str = Depends(oauth2_schema), session = Depends(get_session)):
    try:
        dic_info = jwt.decode(token, SECRET_KEY, ALGORITHM)
        id_user = int(dic_info.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Access denied")
    
    user = session.query(User).filter(User.id==id_user).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid access")
    return user