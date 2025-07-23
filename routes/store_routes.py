from fastapi import APIRouter, Query, Depends
from dependencies import get_session
from sqlalchemy.orm import Session
from repository.store_repository import fetch_nearby_stores, fetch_nearby_branches

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
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    limit: int = None,
    session: Session = Depends(get_session)
):

    return fetch_nearby_branches(
        session=session,
        lat=lat,
        lon=lon,
        limit=limit,
    )