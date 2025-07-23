from fastapi import APIRouter, Query, Depends
from dependencies import get_session
from sqlalchemy.orm import Session
from repository.store_repository import fetch_nearby_stores
from repository.product_repository import fetch_products

home_router = APIRouter(prefix="/home", tags=["home"])

# Rota de lista de produto
@home_router.get("/")
async def get_home(
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):

    return {
        "products": fetch_products(
            session=session,
            lat=lat,
            lon=lon,
        ),
        "nearby_stores": fetch_nearby_stores(
            session=session,
            lat=lat,
            lon=lon,
            limit=10
        )
    }