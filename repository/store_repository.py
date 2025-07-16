from database.models import StoreBranch, StoreBranch
from sqlalchemy import func
from sqlalchemy.orm import Session

def get_nearby_store_branches(lat: float, lon: float, session: Session):
    distance_threshold = 10  # km

    # expressão de distância rotulada
    distance_expr = (
        6371 * func.acos(
            func.cos(func.radians(lat)) * func.cos(func.radians(StoreBranch.latitude)) *
            func.cos(func.radians(StoreBranch.longitude) - func.radians(lon)) +
            func.sin(func.radians(lat)) * func.sin(func.radians(StoreBranch.latitude))
        )
    ).label("distance")

    # montando a query: seleciona a entidade + o distance label
    nearby_store_branches = (
        session.query(StoreBranch, distance_expr)
            .filter(distance_expr <= distance_threshold)
            .order_by("distance")
            .all()
    )

    return nearby_store_branches