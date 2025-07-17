from fastapi import APIRouter, Depends, Query
from dependencies import get_session
from database.models import Product
from sqlalchemy.orm import Session
from routes.utils import haversine, serialize_product_detail, process_products
from repository.store_repository import get_nearby_store_branches
from repository.product_repository import get_store_branch_products
from datetime import date, datetime

product_router = APIRouter(prefix="/product", tags=["products"])

@product_router.get("/")
async def get_products(
    query: str = Query(None, description="Search query for product name"),
    id_category: int = Query(None, description="Filter by category ID"),
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    page: int = Query(1, description="Number of products page"),
    limit: int = Query(5, description="Limit of products per page"),
    session: Session = Depends(get_session)
):
    
    # Obtendo as filiais próximas e produtos correspondentes
    nearby_store_branches = get_nearby_store_branches(lat, lon, session)
    store_branch_products = get_store_branch_products(nearby_store_branches, query, id_category, session)

    return process_products(store_branch_products, lat, lon, page, limit)

@product_router.get("/{id}")
async def get_product(
    id: int,
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    # pega o produto com todas as ofertas
    product = session.query(Product).filter(Product.id == id).first()
    if not product:
        return None

    today = date.today()
    valid_offers = []
    for offer in product.offers:
        # 1) filtra expiração
        exp_date = datetime.strptime(offer.expiration, "%Y-%m-%d").date()
        if exp_date < today:
            continue

        # 2) calcula distância ao store_branch da oferta
        sb = offer.store_branch  # assumindo relacionamento backref
        dist = haversine(lat, lon, sb.latitude, sb.longitude)
        if dist <= 10000:
            valid_offers.append(offer)

    # sobrescreve a lista de offers
    product.offers = valid_offers

    return serialize_product_detail(product, lat, lon)