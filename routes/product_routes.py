from fastapi import APIRouter, Depends, Query
from dependencies import get_session
from database.models import Product, StoreBranch, Store, Category, Offer
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from routes.utils import haversine, list_all_products, list_products_by_store, serialize_product, get_distance_expression
from collections import defaultdict
from datetime import date, datetime

product_router = APIRouter(prefix="/product", tags=["products"])

# Rota de lista de produto
@product_router.get("/")
async def get_list_products(
    id_category: int = Query(None, description="Teste"),
    page: int = Query(1, description="Page", ge=1),
    limit: int = Query(25, description="Page size", ge=1, le=100),
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    
    offset = (page - 1) * limit

    distance_threshold = 10  # km

    # Encontrar filiais próximas usando a fórmula de Haversine
    query = session.query(StoreBranch).filter(
        text(
            "(6371 * acos("
            "cos(radians(:lat)) * cos(radians(latitude)) * "
            "cos(radians(longitude) - radians(:lon)) + "
            "sin(radians(:lat)) * sin(radians(latitude))"
            ")) <= :dist"
        )
    ).params(lat=lat, lon=lon, dist=distance_threshold)
    nearby_store_branches = query.all()

    # Obter os IDs das filiais próximas
    store_branch_ids = [sb.id for sb in nearby_store_branches]

    # Obter ofertas válidas (não expiradas) nas filiais próximas
    today = date.today()
    valid_offers = session.query(Offer).filter(
        Offer.id_store_branch.in_(store_branch_ids),
        text("CAST(expiration AS DATE) >= :today")
    ).params(today=today).all()

    # Agrupar ofertas por produto
    offers_by_product = defaultdict(list)
    for offer in valid_offers:
        offers_by_product[offer.id_product].append(offer)

    # Obter os IDs dos produtos com ofertas válidas
    product_ids = list(offers_by_product.keys())

    # Obter os produtos correspondentes, filtrando por categoria se id_category for fornecido
    query = session.query(Product).filter(Product.id.in_(product_ids))
    if id_category is not None:
        query = query.filter(Product.id_category == id_category)
    products = query.all()

    # Atribuir as ofertas a cada produto
    for product in products:
        product.offers = offers_by_product.get(product.id, [])

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
    sorted_products = sorted(products, key=lambda p: calculate_discount_pct(p.offers), reverse=True)

    # Calcular o total de produtos
    total_products = len(sorted_products)

    # Aplicar paginação: fatiar a lista de produtos
    paginated_products = sorted_products[offset:offset + limit]

    # Serializar os produtos paginados
    serialized_products = [
        serialize_product(product, lat, lon)
        for product in paginated_products
    ]

    # Retornar os produtos paginados com informações de paginação
    return {
        "products": serialized_products,
        "page": page,
        "page_size": limit,
        "total_products": total_products,
        "total_pages": (total_products + limit - 1) // limit
    }

@product_router.get("/categories")
async def get_product_categories(
    session: Session = Depends(get_session)
):
    categories = (
        session.query(Category)
        .order_by(Category.name)
        .all()
    )
    
    return categories
    
@product_router.get("/nearby-stores")
async def get_nearby_stores(
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    store_list_size = 10
    stores = (
        session.query(StoreBranch.id_store, Store.name)
        .join(StoreBranch, Store.id == StoreBranch.id_store)
        .order_by(get_distance_expression(lat, lon, StoreBranch.latitude, StoreBranch.longitude))
        .limit(store_list_size)
        .all()
    )

    return [
        {"id_store" : id_store, "name" : name}
        for id_store, name in stores
    ]

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