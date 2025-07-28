from datetime import datetime, timedelta, timezone
from main import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from jose import jwt
from database.models import User

def create_token(user: User, duration=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    expiration_date = datetime.now(timezone.utc) + duration
    dict_info = { "sub": str(user.id), "name": user.name, "email": user.email, "exp": expiration_date }
    token = jwt.encode(dict_info, SECRET_KEY, ALGORITHM)
    return token

def get_user(email, session):
    user = session.query(User).filter(User.email==email).first()
    if not user:
        return False

    return user