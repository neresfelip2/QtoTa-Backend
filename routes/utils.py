from database.models import Product
from sqlalchemy import func

import math

# Transforma o resultado de uma query na tabela Product num objeto Product
def serialize_product_detail(p: Product, lat: float, lon: float) -> dict:

    prices = [o.price for o in p.offers if o.price is not None]
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
                    "price" : o.price,
                    "discount_percentage": round(
                        ((avg_price - o.price) / avg_price) * 100
                        if avg_price > 0 and o.price is not None
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

def serialize_product(product: Product, lat: float, lon: float) -> dict:
    product.offers.sort(key=lambda offer: offer.price)
    prices = [offer.price for offer in product.offers]
    avg_price = sum(prices) / len(prices) if prices else 0

    best_offer = product.offers[0]

    return {
            "id": product.id,
            "name": product.name,
            "expiration_offer" : best_offer.expiration,
            "price": best_offer.price,
            "percentage": round(((avg_price - best_offer.price) / avg_price) * 100),
            "url_image": product.url_image,
            "store": {
                "id" : best_offer.store.id,
                "name" : best_offer.store.name,
                #"branch" : best_offer.store.store_branch.description,
                "logo" : best_offer.store.logo,
                #"distance" : haversine(lat, lon, best_offer.store_branch.latitude, best_offer.store_branch.longitude),
            }
        
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

def haversine_sql(lat1: float, lon1: float, lat2, lon2):
    return (
        6371000 * func.acos(
            func.cos(func.radians(lat1)) * func.cos(func.radians(lat2)) *
            func.cos(func.radians(lon2) - func.radians(lon1)) +
            func.sin(func.radians(lat1)) * func.sin(func.radians(lat2))
        )
    ).label("distance")

def process_products(products, lat: float, lon: float, page: int, limit: int):
    # Função para calcular a porcentagem de desconto
    def calculate_discount_pct(offers):
        if not offers:
            return 0
        prices = [offer.price for offer in offers if offer.price is not None]
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