from fastapi import APIRouter, Query, Depends
from dependencies import get_session
from sqlalchemy.orm import Session
from routes.product_routes import get_nearby_store_branches, get_store_branch_products, process_products
from database.models import Store

app_router = APIRouter(prefix="/home", tags=["home"])

# Rota de lista de produto
@app_router.get("/")
async def get_home(
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    
    nearby_store_branches = get_nearby_store_branches(lat, lon, session)
    # dicionário para armazenar a menor distância para cada loja
    nearest_nearby_store_branches = {}

    for branch, distance in nearby_store_branches:
        store_id = branch.id_store  # ou branch.store.id, dependendo do modelo
        # se ainda não temos ou esta filial é mais próxima, atualiza
        if store_id not in nearest_nearby_store_branches:
            nearest_nearby_store_branches[store_id] = (branch, distance)
    # store_ids = [sb.id_store for sb, _ in nearby_store_branches]
    # nearby_stores = (
    #     session.query(Store)
    #         .filter(Store.id.in_(store_ids))
    #         .all()
    # )

    store_branch_products = get_store_branch_products(nearby_store_branches, None, session)
    
    categories = set([p.category for p in store_branch_products])

    products = process_products(store_branch_products, lat, lon, page=1, limit=5)

    return {
        "products": products,
        "categories" : categories,
        "nearby_stores" : [
            {
                "id": sb.id_store,
                "name": sb.store.name,
                "distance": round(distance * 1000),  # Convertendo de km para metros
                "logo" : sb.store.logo,
            }
            for sb, distance in nearest_nearby_store_branches.values()
        ],
    }

# # Rota de lista de produto
# @app_router.get("/")
# async def get_list_products(
#     lat: float = Query(description="User latitude"),
#     lon: float = Query(description="User longitude"),
#     session: Session = Depends(get_session)
# ):
    
#     limit = 5
#     distance_threshold = 10  # km

#     # expressão de distância rotulada
#     distance_expr = (
#         6371 * func.acos(
#             func.cos(func.radians(lat)) * func.cos(func.radians(StoreBranch.latitude)) *
#             func.cos(func.radians(StoreBranch.longitude) - func.radians(lon)) +
#             func.sin(func.radians(lat)) * func.sin(func.radians(StoreBranch.latitude))
#         )
#     ).label("distance")

#     # montando a query: seleciona a entidade + o distance label
#     nearby_store_branches = (
#         session.query(StoreBranch, distance_expr)
#             .filter(distance_expr <= distance_threshold)
#             .all()
#     )

#     # Obter os IDs das filiais próximas
#     store_branch_ids = [sb.id for sb, _ in nearby_store_branches]

#     # Obter os produtos correspondentes
#     today = date.today()
#     products = (
#         session.query(Product)
#             .join(Offer, Offer.id_product == Product.id)
#             .filter(
#                 Offer.id_store_branch.in_(store_branch_ids),
#                 Offer.expiration >= today,
#             )
#             .options(contains_eager(Product.offers))
#             .all()
#     )

#     # Função para calcular a porcentagem de desconto
#     def calculate_discount_pct(offers):
#         if not offers:
#             return 0
#         prices = [offer.current_price for offer in offers if offer.current_price is not None]
#         if not prices:
#             return 0
#         min_price = min(prices)
#         avg_price = sum(prices) / len(prices)
#         if avg_price == 0:
#             return 0
#         return ((avg_price - min_price) / avg_price) * 100

#     # Ordenar os produtos pela porcentagem de desconto em ordem decrescente
#     sorted_products = sorted(products, key=lambda p: calculate_discount_pct(p.offers), reverse=True)[:limit]

#     # Serializar os produtos paginados
#     serialized_products = [
#         serialize_product(product, lat, lon)
#         for product in sorted_products
#     ]

#     categories = set([p.category for p in products])

#     return {
#         "products": serialized_products,
#         "categories" : categories,
#         "nearby_stores" : [
#             {
#                 "id": sb.id,
#                 "name": sb.store.name,
#                 "branch": sb.description,
#                 "distance": round(distance * 1000),  # Convertendo de km para metros
#                 "logo" : sb.store.logo,
#             }
#             for sb, distance in nearby_store_branches
#         ],
#     }