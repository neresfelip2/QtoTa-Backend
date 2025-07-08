from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Substitua com as suas credenciais e banco
# DATABASE_URL = "mysql+pymysql://usuario:senha@localhost:3306/nome_do_banco"
DATABASE_URL = "mysql+pymysql://root@localhost:3306/qtota"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
Base.metadata.create_all(bind=engine)
