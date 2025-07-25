from fastapi import APIRouter, Query, Depends, HTTPException
from dependencies import get_session
from sqlalchemy import func
from sqlalchemy.orm import Session, contains_eager
from repository.store_repository import fetch_nearby_stores, fetch_nearby_branches
from database.models import Offer, Store, StoreBranch, Product
from routes.utils import haversine_sql, haversine

store_router = APIRouter(prefix="/store", tags=["store"])

@store_router.get("/")
async def get_nearby_stores(
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    limit: int = None,
    session: Session = Depends(get_session)
):

    return fetch_nearby_stores(
        session=session,
        lat=lat,
        lon=lon,
        limit=limit,
    )

@store_router.get("/branches")
async def get_nearby_branches(
    store_id: int = Query(None, description="Filter by store"),
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    limit: int = None,
    session: Session = Depends(get_session)
):

    return fetch_nearby_branches(
        session=session,
        store_id=store_id,
        lat=lat,
        lon=lon,
        limit=limit,
    )

@store_router.get("/{id}")
async def get_store_detail(
    id: int,
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    
    distance_expr = haversine_sql(lat, lon, StoreBranch.latitude, StoreBranch.longitude)
    
    store = (
        session.query(Store)
            .join(StoreBranch, StoreBranch.id_store == Store.id)
            .outerjoin(Offer, Offer.id_store == Store.id)
            .outerjoin(Product, Product.id == Offer.id_product)
            .options(
                contains_eager(Store.branches),
                contains_eager(Store.offers)
                    .contains_eager(Offer.product),
            )
            .filter(Store.id == id, distance_expr <= 10000)
            .order_by(distance_expr)
            .one_or_none()
    )
    
    if store:
        # Adicionar a distância a cada filial
        for branch in store.branches:
            branch.distance = haversine(lat, lon, branch.latitude, branch.longitude)

        # Calcular a porcentagem para cada oferta
        for offer in store.offers:
            # Calcular a média dos preços das ofertas desse produto em outras lojas
            avg_price = session.query(func.avg(Offer.price)).filter(
                Offer.id_product == offer.id_product,
                #Offer.id_store != id
            ).scalar()
            
            if avg_price:
                percentage = (1 - offer.price / avg_price) * 100
            else:
                percentage = 0  # Se não houver outras ofertas, a porcentagem é 0

            offer.percentage = percentage

        return {
            "id": store.id,
            "name": store.name,
            "logo": store.logo,
            "branches": store.branches,
            "products": [
                {
                    "id": offer.product.id,
                    "name": offer.product.name,
                    "url_image": offer.product.url_image,
                    "price": offer.price,
                    "percentage": round(offer.percentage),
                }
                for offer in store.offers
            ]
        }
    else:
        raise HTTPException(status_code=404, detail="Store not found")