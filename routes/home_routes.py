from fastapi import APIRouter, Query, Depends
from dependencies import get_session
from sqlalchemy.orm import Session, joinedload
from repository.store_repository import get_nearby_store_branches
from repository.product_repository import get_store_branch_products
from routes.utils import process_products, haversine_sql

home_router = APIRouter(prefix="/home", tags=["home"])

# Rota de lista de produto
@home_router.get("/")
async def get_home(
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    
    # Obter as filiais próximas e produtos correspondentes
    nearby_store_branches = get_nearby_store_branches(lat, lon, session)
    store_branch_products = get_store_branch_products(nearby_store_branches, None, None, session)
    
    # Obtendo as categorias dos produtos das filiais
    categories = set([p.category for p in store_branch_products])

    # Processando produtos para a página inicial
    products = process_products(store_branch_products, lat, lon, page=1, limit=5)   
    
    # dicionário para armazenar a menor distância para cada loja
    nearest_nearby_store_branches = {}
    for branch, distance in nearby_store_branches:
        store_id = branch.id_store     
        if store_id not in nearest_nearby_store_branches:
            nearest_nearby_store_branches[store_id] = (branch, distance)

    return {
        "products": products,
        "categories" : categories,
        "nearby_stores" : [
            {
                "id": sb.id_store,
                "name": sb.store.name,
                "distance": round(distance),
                "logo" : sb.store.logo,
            }
            for sb, distance in nearest_nearby_store_branches.values()
        ],
    }