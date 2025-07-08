from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from dependencies import get_session
from models import Product, Offer, StoreBranch
import math
from sqlalchemy import func

product_router = APIRouter(prefix="/product", tags=["products"])

# Rota de lista de produto
@product_router.get("/")
async def get_list_products(
    page: int = Query(1, description="Page", ge=1),
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    
    page_size = 5
    offset = (page - 1) * page_size
    
    # 1) Subquery: para cada produto, qual é o menor preço?
    min_price_sq = (
        session.query(
            Offer.id_product.label("pid"),
            func.min(Offer.current_price).label("min_price")
        )
        .group_by(Offer.id_product)
        .subquery()
    )

    # 2) Faça o join de Offer com essa subquery, garantindo que
    #    Offer.current_price == subquery.min_price
    #    Depois junte com StoreBranch e calcule a distância.
    distance_expr = func.round(
        6371000 * 2 * func.asin(
            func.sqrt(
                func.pow((func.radians(StoreBranch.latitude) - func.radians(lat)) / 2, 2)
                + func.cos(func.radians(lat)) * func.cos(func.radians(StoreBranch.latitude))
                * func.pow((func.radians(StoreBranch.longitude) - func.radians(lon)) / 2, 2)
            )
        )
    ).label("distance")

    results = (
        session.query(
            Offer.id_product,
            Offer.id_store_branch
        )
        # join no subquery de preços mínimos
        .join(min_price_sq, 
            (Offer.id_product == min_price_sq.c.pid) &
            (Offer.current_price == min_price_sq.c.min_price)
        )
        # join na tabela de filiais
        .join(StoreBranch, Offer.id_store_branch == StoreBranch.id)
        .order_by(distance_expr)
        .limit(page_size)
        .offset(offset)
        .all()
    )

    # 4) lista de produtos a ser mostrada ao usuário
    product_ids = [prod_id for prod_id, _ in results]
    products = (
        session
            .query(Product)
            .filter(Product.id.in_(product_ids))
            .order_by(func.field(Product.id, *product_ids))
            .all()
        )
    
    return [serialize_product(product, lat, lon) for product in products]

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

# Transforma o resultado de uma query na tabela Product num objeto Product
def serialize_product(p: Product, lat: float, lon: float) -> dict:
    return {
            "id": p.id,
            "name": p.name,
            "description" : p.description,
            "weight": p.weight,
            "type" : p.type,
            "origin" : p.origin,
            "expiration": p.expiration,
            "stores" : [
                {
                    "id" : o.id_store_branch,
                    "name" : o.store_branch.store.name,
                    "branch" : o.store_branch.description,
                    "current_price" : o.current_price,
                    "previous_price" : o.previous_price,
                    "expiration_offer" : o.expiration,
                    "logo" : o.store_branch.store.logo,
                    "distance" : haversine(lat, lon, o.store_branch.latitude, o.store_branch.longitude),
                }
                for o in p.offers
            ]
        }

# Cálculo da distância entre duas coordenadas geográficas
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:

    # converte graus para radianos
    φ1, λ1 = math.radians(lat1), math.radians(lon1)
    φ2, λ2 = math.radians(lat2), math.radians(lon2)

    # diferenças
    Δφ = φ2 - φ1
    Δλ = λ2 - λ1

    # haversine
    a = math.sin(Δφ / 2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    # raio médio da Terra em metros
    R = 6_371_000

    return int(R * c)