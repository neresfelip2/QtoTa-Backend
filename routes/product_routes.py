from fastapi import APIRouter, Depends, Query
from dependencies import get_session
from database.models import Product, StoreBranch, Store
from sqlalchemy.orm import Session
from routes.utils import list_all_products, list_products_by_store, serialize_product, get_distance_expression

product_router = APIRouter(prefix="/product", tags=["products"])

# Rota de lista de produto
@product_router.get("/")
async def get_list_products(
    id_store: int = Query(None, description="Teste"),
    page: int = Query(1, description="Page", ge=1),
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    page_size = 50
    offset = (page - 1) * page_size

    if not id_store:
        return list_all_products(page_size, offset, lat, lon, session)
    else:
        return list_products_by_store(id_store, page_size, offset, lat, lon, session)
    
@product_router.get("/nearby-stores")
async def get_nearby_stores(
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    store_list_size = 10
    stores = (
        session.query(StoreBranch.id_store, Store.name)
        .join(StoreBranch, Store.id == StoreBranch.id_store)
        .order_by(get_distance_expression(lat, lon, StoreBranch.latitude, StoreBranch.longitude))
        .limit(store_list_size)
        .all()
    )

    return [
        {"id_store" : id_store, "name" : name}
        for id_store, name in stores
    ]

# Rota de busca de produto único
@product_router.get("/{id}")
async def get_product(
    id: int,
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    product = (
        session.query(Product)
            .filter(Product.id == id)
            .first()
    )
    
    return serialize_product(product, lat, lon)