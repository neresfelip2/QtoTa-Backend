from database.models import Product, Offer, StoreBranch, Store
from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session
from routes.utils import haversine_sql

def fetch_products(
    session: Session,
    lat: float,
    lon: float,
    page: int = 1,
    limit: int = 5,
    distance_threshold: int = 10,
    query: str | None = None,
    id_category: int | None = None,
):
    distance_expr = haversine_sql(lat, lon, StoreBranch.latitude, StoreBranch.longitude)

    # 1) subquery com row_number
    subq_branches = (
        session.query(
            Store.id,
            Store.name,
            StoreBranch.description,
            Store.logo,
            distance_expr.label("distance"),
            func.row_number()
                .over(
                    partition_by=StoreBranch.id_store,
                    order_by=distance_expr.asc()
                )
                .label("rn")
        )
        .join(Store, Store.id == StoreBranch.id_store)
        .subquery()
    )

    # 2) consulta final: só rn = 1
    subq_stores = (
        session.query(
            subq_branches.c.id,
            subq_branches.c.name,
            subq_branches.c.description,
            subq_branches.c.logo,
            subq_branches.c.distance
        )
        .filter(subq_branches.c.rn == 1)
        .order_by(subq_branches.c.id)
        .subquery()
    )

    subq_min_price = (
        session.query(
            Offer.id_product.label("pid"),
            func.min(Offer.price).label("min_price"),
            ((1 - func.min(Offer.price)/func.avg(Offer.price)) * 100).label("percentage")
        )
        .group_by(Offer.id_product)
        .subquery()
    )

    product_filters = [
        subq_stores.c.distance <= distance_threshold * 1000
    ]

   # 3) Filtro por nome (accent‑ and case‑insensitive)
    if query:
        product_filters.append(
            func.unaccent(Product.name).ilike(func.unaccent(f"%{query}%"))
        )
    # filtrar por categoria, se fornecido
    if id_category:
        product_filters.append(Product.id_category == id_category)

    # Join Product → Offer → subquery, casando product_id e price == min_price
    products_query = (
        session.query(Product, Offer, subq_min_price.c.percentage, subq_stores.c.name, subq_stores.c.description, subq_stores.c.distance, subq_stores.c.logo)
        .join(Offer, Offer.id_product == Product.id)
        .join(
            subq_min_price,
            and_(
                Offer.id_product == subq_min_price.c.pid,
                Offer.price      == subq_min_price.c.min_price
            )
        )
        .join(subq_stores, Offer.id_store == subq_stores.c.id)
        .order_by(desc(subq_min_price.c.percentage))
        .filter(*product_filters)
        .offset((page - 1) * limit)
        .limit(limit)
    )

    # Executa e empacota o resultado
    return [
        {
            "id": prod.id,
            "name": prod.name,
            "expiration_offer": offer.expiration,
            "price": offer.price,
            "percentage": round(percentage),
            "url_image": prod.url_image,
            "store" : {
                "id": offer.id_store,
                "name": store,
                "branch": branch,
                "distance": round(distance),
                "logo": url_logo
            }
        }
        for prod, offer, percentage, store, branch, distance, url_logo in products_query.all()
    ]