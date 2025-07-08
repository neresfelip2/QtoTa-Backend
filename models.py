from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship
from database import Base

# Tabela Product
class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    weight = Column(Integer, nullable=False)
    type = Column(String(255), nullable=False)
    origin = Column(String(255), nullable=False)
    expiration = Column(Integer, nullable=False)

    # Relacionamento 1:N com Offer
    offers = relationship(
        "Offer",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

# Tabela Store
class Store(Base):
    __tablename__ = "store"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    logo = Column(String(255))

    # Relacionamento 1:N com StoreBranch
    branches = relationship(
        "StoreBranch",
        back_populates="store",
        cascade="all, delete-orphan"
    )

    def __init__(self, name: str):
        self.name = name

# Tabela StoreBranch
class StoreBranch(Base):
    __tablename__ = "store_branch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_store = Column(
        Integer,
        ForeignKey(
            "store.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=False
    )
    description = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Relacionamentos
    store = relationship(
        "Store",
        back_populates="branches"
    )
    offers = relationship(
        "Offer",
        back_populates="store_branch",
        cascade="all, delete-orphan"
    )

    def __init__(self, id_store: int, description: str, latitude: float, longitude: float):
        self.id_store = id_store
        self.description = description
        self.latitude = latitude
        self.longitude = longitude

# Tabela Offer
class Offer(Base):
    __tablename__ = "offer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_product = Column(
        Integer,
        ForeignKey(
            "product.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=False
    )
    id_store_branch = Column(
        Integer,
        ForeignKey(
            "store_branch.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=False
    )
    current_price = Column(Float, nullable=False)
    previous_price = Column(Float, nullable=True)
    expiration = Column(String(10), nullable=False)

    # Relacionamentos
    product = relationship(
        "Product",
        back_populates="offers"
    )
    store_branch = relationship(
        "StoreBranch",
        back_populates="offers"
    )

    def __init__(self, id_product: int, id_store_branch: int, current_value: float, previous_value: float = None):
        self.id_product = id_product
        self.id_store_branch = id_store_branch
        self.current_value = current_value
        self.previous_value = previous_value

# Tabela User
class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)

    def __init__(self, name: str, email: str, password: str):
        self.name = name
        self.email = email
        self.password = password