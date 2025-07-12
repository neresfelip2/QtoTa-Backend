from fastapi import APIRouter, Query, Depends
from dependencies import get_session
from sqlalchemy import func
from sqlalchemy.orm import Session, contains_eager
from database.models import StoreBranch, Product, Offer, Category
from datetime import date
from routes.utils import serialize_product

app_router = APIRouter(prefix="/home", tags=["home"])

# Rota de lista de produto
@app_router.get("/")
async def get_list_products(
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    
    limit_products = 5
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
            .all()
    )

    # Obter os IDs das filiais próximas
    store_branch_ids = [sb.id for sb, _ in nearby_store_branches]

    # Obter os produtos correspondentes
    today = date.today()
    products = (
        session.query(Product)
            .join(Offer, Offer.id_product == Product.id)
            .filter(
                Offer.id_store_branch.in_(store_branch_ids),
                Offer.expiration >= today,
            )
            .options(contains_eager(Product.offers))
            .all()
    )

    # Função para calcular a porcentagem de desconto
    def calculate_discount_pct(offers):
        if not offers:
            return 0
        prices = [offer.current_price for offer in offers if offer.current_price is not None]
        if not prices:
            return 0
        min_price = min(prices)
        avg_price = sum(prices) / len(prices)
        if avg_price == 0:
            return 0
        return ((avg_price - min_price) / avg_price) * 100

    # Ordenar os produtos pela porcentagem de desconto em ordem decrescente
    sorted_products = sorted(products, key=lambda p: calculate_discount_pct(p.offers), reverse=True)[:limit_products]

    # Serializar os produtos paginados
    serialized_products = [
        serialize_product(product, lat, lon)
        for product in sorted_products
    ]

    categories = set([p.category for p in products])

    return {
        "products": serialized_products,
        "categories" : categories,
        "nearby_stores" : [
            {
                "id": sb.id,
                "name": sb.store.name,
                "branch": sb.description,
                "distance": round(distance * 1000),  # Convertendo de km para metros
                "logo" : sb.store.logo,
            }
            for sb, distance in nearby_store_branches
        ],
    }