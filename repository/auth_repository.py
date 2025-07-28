from datetime import datetime, timedelta, timezone
from main import bcrypt_context, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from jose import jwt
from database.models import User

def create_token(id_user, duration=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    expiration_date = datetime.now(timezone.utc) + duration
    dict_info = { "sub": str(id_user), "exp": expiration_date }
    token = jwt.encode(dict_info, SECRET_KEY, ALGORITHM)
    return token

def get_user(email, session):
    user = session.query(User).filter(User.email==email).first()
    if not user:
        return False

    return user