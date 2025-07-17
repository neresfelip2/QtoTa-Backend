from database.models import StoreBranch, StoreBranch
from sqlalchemy.orm import Session
from routes.utils import haversine_sql

def get_nearby_store_branches(lat: float, lon: float, session: Session):
    distance_threshold = 10000  # metros

    # expressão de distância rotulada
    distance_expr = haversine_sql(lat, lon, StoreBranch.latitude, StoreBranch.longitude)

    # montando a query: seleciona a entidade + o distance label
    nearby_store_branches = (
        session.query(StoreBranch, distance_expr)
            .filter(distance_expr <= distance_threshold)
            .order_by("distance")
            .all()
    )

    return nearby_store_branches