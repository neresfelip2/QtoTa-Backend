from fastapi import APIRouter, Depends, Query
from dependencies import get_session
from database.models import Product, StoreBranch, Store, Category, Offer
from sqlalchemy.orm import Session, contains_eager
from sqlalchemy import func
from routes.utils import haversine, serialize_product, get_distance_expression
from datetime import date, datetime

product_router = APIRouter(prefix="/product", tags=["products"])

@product_router.get("/")
async def get_products(
    id_category: int = Query(None, description="Filter by category ID"),
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    page: int = Query(1, description="Number of products page"),
    limit: int = Query(5, description="Limit of products per page"),
    session: Session = Depends(get_session)
):
    
    # Obter as filiais próximas
    nearby_store_branches = get_nearby_store_branches(lat, lon, session)

    # Obter os produtos correspondentes
    store_branch_products = get_store_branch_products(nearby_store_branches, id_category, session)

    return process_products(store_branch_products, lat, lon, page, limit)

def process_products(products, lat: float, lon: float, page: int, limit: int):
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

    # Ordenar os produtos pela porcentagem de desconto
    sorted_products = sorted(
        products,
        key=lambda p: calculate_discount_pct(p.offers),
        reverse=True
    )

    # cálculo do offset e do tamanho da página
    start = (page - 1) * limit
    end = start + limit

    # fatiar a lista para pegar apenas a "página" desejada
    paginated_products = sorted_products[start:end]

    # Serializar os produtos da página
    serialized_products = [
        serialize_product(product, lat, lon)
        for product in paginated_products
    ]

    return serialized_products
    
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

def get_store_branch_products(nearby_store_branches, id_category, session: Session):

    # Obter os IDs das filiais próximas
    store_branch_ids = [sb.id for sb, _ in nearby_store_branches]

    today = date.today()
    product_filters = [
        Offer.id_store_branch.in_(store_branch_ids),
        Offer.expiration >= today
    ]

    # só adiciona o filtro de categoria se vier no request
    if id_category is not None:
        product_filters.append(Product.id_category == id_category)

    products = (
        session.query(Product)
            .join(Offer, Offer.id_product == Product.id)
            .filter(*product_filters)
            .options(contains_eager(Product.offers))
            .all()
    )
    return products

@product_router.get("/{id}")
async def get_product(
    id: int,
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    # pega o produto com todas as ofertas
    product = session.query(Product).filter(Product.id == id).first()
    if not product:
        return None

    today = date.today()
    valid_offers = []
    for offer in product.offers:
        # 1) filtra expiração
        exp_date = datetime.strptime(offer.expiration, "%Y-%m-%d").date()
        if exp_date < today:
            continue

        # 2) calcula distância ao store_branch da oferta
        sb = offer.store_branch  # assumindo relacionamento backref
        dist = haversine(lat, lon, sb.latitude, sb.longitude)
        if dist <= 10000:
            valid_offers.append(offer)

    # sobrescreve a lista de offers
    product.offers = valid_offers

    return serialize_product(product, lat, lon)