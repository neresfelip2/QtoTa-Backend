from pydantic import BaseModel

# Register User
class UserScheme(BaseModel):
    name: str
    email: str
    password: str

    class Config:
        from_attributes = True

# Login
class LoginSchema(BaseModel):
    email: str
    password: str

    class Config:
        from_attributes = True