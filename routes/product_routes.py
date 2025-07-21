from fastapi import APIRouter, Depends, Query
from dependencies import get_session
from database.models import Product, Category, Offer, Store
from sqlalchemy.orm import Session, joinedload
from repository.product_repository import fetch_products
from routes.utils import haversine

product_router = APIRouter(prefix="/product", tags=["products"])


############### Recuperar a lista de produtos por maior percentagem de desconto ###############

@product_router.get("/")
async def get_products(
    query: str = Query(None, description="Search query for product name"),
    id_category: int = Query(None, description="Filter by category ID"),
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    page: int = Query(1, description="Number of products page"),
    limit: int = Query(10, description="Limit of products per page"),
    distance_threshold: int = Query(10, description="Max distance by km"),
    session: Session = Depends(get_session)
):
    
    return fetch_products(
        session=session,
        lat=lat,
        lon=lon,
        page=page,
        limit=limit,
        distance_threshold=distance_threshold,
        query=query,
        id_category=id_category
    )

@product_router.get("/category")
async def get_categories(
    session: Session = Depends(get_session)
):
    categories = (
        session
            .query(Category)
            .order_by(Category.name)
            .all()
        )
    return categories


############### Recuperar um produto específico ###############

@product_router.get("/{id}")
async def get_product(
    id: int,
    lat: float = Query(description="User latitude"),
    lon: float = Query(description="User longitude"),
    session: Session = Depends(get_session)
):
    # pega o produto com todas as ofertas
    product = (
        session.query(Product)
            .join(Offer, Offer.id_product == Product.id)
            .options(
                joinedload(Product.offers)
                    .joinedload(Offer.store)
                        .joinedload(Store.branches)
            )
            .filter(Product.id == id)
            .first()
    )
    if not product:
        return None
    
    product.offers.sort(key=lambda o: o.price)

    # 3) para cada oferta, encontra a branch mais próxima
    stores_data = []
    for offer in product.offers:
        branches = offer.store.branches
        # encontra a branch com menor distância
        nearest = min(
            branches,
            key=lambda b: haversine(lat, lon, b.latitude, b.longitude)
        )
        # calcula distância para exibir
        dist_m = haversine(lat, lon, nearest.latitude, nearest.longitude)

        stores_data.append({
            "id":       offer.store.id,
            "name":     offer.store.name,
            "branch":   nearest.description,
            "distance": round(dist_m),           # metros, sem decimais
            "price":    offer.price,
            "logo":     offer.store.logo,
            "expiration_offer": offer.expiration
        })

    # 4) monta dicionário final
    return {
        "id":           product.id,
        "name":         product.name,
        "description":  product.description,
        "measure":      product.measure,
        "measure_type": product.measure_type,
        "type":         product.type,
        "origin":       product.origin,
        "expiration":   product.expiration,
        "url_image":    product.url_image,
        "stores":       stores_data
    }
