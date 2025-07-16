from database.models import Product, Offer, StoreBranch, StoreBranch
from sqlalchemy import func
from sqlalchemy.orm import aliased, Session, contains_eager
from datetime import date

import math

def list_all_products(page_size, offset, lat, lon, session):
    # 1) Subquery: para cada produto, qual é o menor preço?
    min_price_sq = (
        session.query(
            Offer.id_product.label("pid"),
            func.min(Offer.current_price).label("min_price")
        )
        .group_by(Offer.id_product)
        .subquery()
    )

    # 2) Faça o join de Offer com essa subquery, garantindo que
    #    Offer.current_price == subquery.min_price
    #    Depois junte com StoreBranch e calcule a distância.
    distance_expr = get_distance_expression(
        lat, lon,
        StoreBranch.latitude, StoreBranch.longitude,
    )

    results = (
        session.query(
            Offer.id_product,
            Offer.id_store_branch
        )
        # join no subquery de preços mínimos
        .join(min_price_sq, 
            (Offer.id_product == min_price_sq.c.pid) &
            (Offer.current_price == min_price_sq.c.min_price)
        )
        # join na tabela de filiais
        .join(StoreBranch, Offer.id_store_branch == StoreBranch.id)
        .order_by(distance_expr)
        .limit(page_size)
        .offset(offset)
        .all()
    )

    if not results:
        return []

    # 4) lista de produtos a ser mostrada ao usuário
    product_ids = [prod_id for prod_id, _ in results]
    products = (
        session
            .query(Product)
            .filter(Product.id.in_(product_ids))
            .order_by(func.field(Product.id, *product_ids))
            .all()
        )
    
    return [serialize_product(product, lat, lon) for product in products]

def list_products_by_store(id_store, page_size, offset, lat, lon, session):
    SB2 = aliased(StoreBranch)
    O2 = aliased(Offer)
    P = aliased(Product)
    SB3 = aliased(StoreBranch)
    O3 = aliased(Offer)

    # Subquery para obter o menor preço por produto na mesma loja (id_store)
    subq = (
        session.query(func.min(O3.current_price))
        .join(SB3, SB3.id == O3.id_store_branch)
        .filter(
            O3.id_product == O2.id_product,
            SB3.id_store == id_store
        )
        .scalar_subquery()
    )

    # Cálculo da distância em metros pelo Haversine
    distance_expr = get_distance_expression(lat, lon, SB2.latitude, SB2.longitude)

    # Query principal: inicia a partir de SB2 para evitar aliases duplicados
    results = (
        session.query(P.id)
        .select_from(SB2)
        .join(O2, O2.id_store_branch == SB2.id)
        .join(P, P.id == O2.id_product)
        .filter(O2.current_price == subq)
        .order_by(distance_expr)
        .limit(page_size)
        .offset(offset)
        .all()
    )

    if not results:
        return []

    # Extrai IDs (cada resultado é tupla: (id,))
    product_ids = [r[0] for r in results]

    # Busca objetos Product e preserva a ordem original usando FIELD (MySQL)
    products = (
        session
        .query(Product)
        .filter(Product.id.in_(product_ids))
        .order_by(func.field(Product.id, *product_ids))
        .all()
    )

    # Serializa e retorna
    return [serialize_product(product, lat, lon) for product in products]

# Transforma o resultado de uma query na tabela Product num objeto Product
def serialize_product(p: Product, lat: float, lon: float) -> dict:

    prices = [o.current_price for o in p.offers if o.current_price is not None]
    avg_price = sum(prices) / len(prices) if prices else 0

    return {
            "id": p.id,
            "name": p.name,
            "description" : p.description,
            "measure": p.measure,
            "measure_type": p.measure_type,
            "type" : p.type,
            "origin" : p.origin,
            "expiration": p.expiration,
            "url_image": p.url_image,
            "stores" : [
                {
                    "id" : o.store_branch.id_store,
                    "name" : o.store_branch.store.name,
                    "branch" : o.store_branch.description,
                    "current_price" : o.current_price,
                    "discount_percentage": round(
                        ((avg_price - o.current_price) / avg_price) * 100
                        if avg_price > 0 and o.current_price is not None
                        else 0
                    ),
                    "previous_price" : 0,
                    "expiration_offer" : o.expiration,
                    "logo" : o.store_branch.store.logo,
                    "distance" : haversine(lat, lon, o.store_branch.latitude, o.store_branch.longitude),
                }
                for o in p.offers
            ]
        }

# Cálculo da distância entre duas coordenadas geográficas
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:

    # converte graus para radianos
    φ1, λ1 = math.radians(lat1), math.radians(lon1)
    φ2, λ2 = math.radians(lat2), math.radians(lon2)

    # diferenças
    Δφ = φ2 - φ1
    Δλ = λ2 - λ1

    # haversine
    a = math.sin(Δφ / 2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    # raio médio da Terra em metros
    R = 6_371_000

    return int(R * c)

def haversine_sql(lat1: float, lon1: float, lat2: float, lon2: float):
    return func.round(
        6371000 * 2 * func.asin(
            func.sqrt(
                func.power((func.radians(lat2) - func.radians(lat1)) / 2, 2)
                + func.cos(func.radians(lat1)) * func.cos(func.radians(lat2))
                * func.power((func.radians(lon2) - func.radians(lon1)) / 2, 2)
            )
        )
    ).label('distance')

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

def get_store_branch_products(nearby_store_branches, query: str, id_category: int, session: Session):

    # Obter os IDs das filiais próximas
    store_branch_ids = [sb.id for sb, _ in nearby_store_branches]

    today = date.today()
    product_filters = [
        Offer.id_store_branch.in_(store_branch_ids),
        Offer.expiration >= today
    ]
    
   # 3) Filtro por nome (accent‑ and case‑insensitive)
    if query:
        product_filters.append(
            # aplica collation accent-insensitive diretamente na coluna
            Product.name
                   .collate("Latin1_General_CI_AI")
                   .ilike(f"%{query}%")
        )

    # filtrar por categoria, se fornecido
    if id_category:
        product_filters.append(Product.id_category == id_category)

    products = (
        session.query(Product)
            .join(Offer, Offer.id_product == Product.id)
            .filter(*product_filters)
            .options(contains_eager(Product.offers))
            .all()
    )
    return products