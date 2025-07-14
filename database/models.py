from sqlalchemy import Column, ForeignKey, Integer, String, Float, Enum
from sqlalchemy.orm import relationship
from database.database import Base
import enum

class MeasureType(enum.Enum):
    WEIGHT = "WEIGHT"
    VOLUME = "VOLUME"
    LENGTH = "LENGTH"

# Tabela Category
class Category(Base):
    __tablename__ = "category"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url_icon = Column(String(255))
    products = relationship(
        "Product",
        back_populates="category",
        cascade="all, delete-orphan"
    )

    def __init__(self, name: str):
        self.name = name

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

# Tabela Product
class Product(Base):
    __tablename__ = "product"

    MEASURE_TYPES = (
        ("WEIGHT", "WEIGHT"),
        ("VOLUME", "VOLUME"),
        ("LENGTH", "LENGTH"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    measure = Column(Integer, nullable=False)
    measure_type = Column(Enum(MeasureType, name="measure_type_enum"), nullable=False)
    type = Column(String(255), nullable=False)
    origin = Column(String(255), nullable=False)
    expiration = Column(Integer, nullable=False)
    url_image = Column(String(255), nullable=True)
    id_category = Column(
        Integer,
        ForeignKey(
            "category.id",
            onupdate="CASCADE",
            ondelete="SET NULL"
        ),
        nullable=True
    )

    # Relacionamento 1:N com Offer
    offers = relationship(
        "Offer",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    # Relacionamento N:1 com Category
    category = relationship(
        "Category",
        back_populates="products"
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

# Migração comando
# python -m alembic revision --autogenerate -m "First Migration"
# python -m alembic upgrade head