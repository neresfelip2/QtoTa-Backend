from fastapi import APIRouter, Query, Depends
from dependencies import get_session
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from database.models import StoreBranch
from routes.utils import haversine_sql

store_router = APIRouter(prefix="/store", tags=["store"])

@store_router.get("/")
async def get_nearby_stores(
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):

    # Expressão de cálculo da distância (fórmula de Haversine)
    distance_expr = haversine_sql(lat, lon, StoreBranch.latitude, StoreBranch.longitude)

    # Subconsulta para encontrar a distância mínima por loja
    min_distance_subquery = session.query(
        StoreBranch.id_store,
        func.min(distance_expr).label('min_distance')
    ).group_by(StoreBranch.id_store).subquery()

    # Consulta principal
    query = session.query(StoreBranch, distance_expr.label('distance')).options(
        joinedload(StoreBranch.store)
    ).join(
        min_distance_subquery,
        StoreBranch.id_store == min_distance_subquery.c.id_store
    ).filter(distance_expr == min_distance_subquery.c.min_distance).order_by('distance')

    # Execução da consulta
    results = query.all()

    return [
        {
            "id": branch.id_store,
            "name": branch.store.name,
            "logo": branch.store.logo,
            "distance": round(distance),
        }
        for branch, distance in results
    ]