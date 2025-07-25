from database.models import Store, StoreBranch
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from routes.utils import haversine_sql

def fetch_nearby_stores(
    session: Session,
    lat: float,
    lon: float,
    limit: int = None,
):
    distance_threshold = 10000  # metros

    # expressão de distância rotulada
    distance_expr = haversine_sql(lat, lon, StoreBranch.latitude, StoreBranch.longitude)

    # subquery: para cada loja, calcula a menor distância
    subq = (
        session
        .query(
            StoreBranch.id_store.label("id_store"),
            func.min(distance_expr).label("min_dist")
        )
        .group_by(StoreBranch.id_store)
        .subquery()
    )

    # join da subquery para pegar só as filiais cuja distância = min_dist
    qry = (
        session
        .query(
            Store,
            StoreBranch,
            subq.c.min_dist.label("distance")
        )
        .join(StoreBranch, StoreBranch.id_store == Store.id)
        # junta com o resultado da subquery:
        .join(
            subq,
            and_(
                StoreBranch.id_store == subq.c.id_store,
                distance_expr == subq.c.min_dist
            )
        )
        # filtra só até o threshold
        .filter(subq.c.min_dist <= distance_threshold)
        .order_by(subq.c.min_dist)
        .limit(limit)
    )

    return [
        {
            "id": store.id,
            "name": store.name,
            "latitude": branch.latitude,
            "longitude": branch.longitude,
            "distance": round(distance),
            "logo" : store.logo,
        }
        for store, branch, distance in qry
    ]

def fetch_nearby_branches(
    session: Session,
    lat: float,
    lon: float,
    limit: int = None,
):
    distance_threshold = 10000  # metros

    # expressão de distância rotulada
    distance_expr = haversine_sql(lat, lon, StoreBranch.latitude, StoreBranch.longitude)

    qry = (
        session
        .query(
            Store,
            StoreBranch,
            distance_expr
        )
        .join(StoreBranch, StoreBranch.id_store == Store.id)
        .filter(distance_expr <= distance_threshold)
        .order_by("distance")
        .limit(limit)
    )

    return [
        {
            "id": store.id,
            "name": store.name,
            "latitude": branch.latitude,
            "longitude": branch.longitude,
            "distance": round(distance),
            "logo" : store.logo,
        }
        for store, branch, distance in qry
    ]