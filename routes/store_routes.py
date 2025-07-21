from fastapi import APIRouter, Query, Depends
from dependencies import get_session
from sqlalchemy.orm import Session
from repository.store_repository import fetch_nearby_stores

store_router = APIRouter(prefix="/store", tags=["store"])

@store_router.get("/")
async def get_nearby_stores(
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):

    return fetch_nearby_stores(
        session=session,
        lat=lat,
        lon=lon,
    )