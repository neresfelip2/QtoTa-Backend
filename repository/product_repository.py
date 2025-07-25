from database.models import Product, Offer, StoreBranch, Store
from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session
from routes.utils import haversine_sql

def fetch_products(
    session: Session,
    lat: float,
    lon: float,
    page: int = 1,
    limit: int = 4,
    distance_threshold: int = 5000,
    query: str | None = None,
    id_store: int | None = None,
    id_category: int | None = None,
):
    # expressão de distância (haversine)
    distance_expr = haversine_sql(lat, lon, StoreBranch.latitude, StoreBranch.longitude)

    # filtros iniciais (loja selecionada)
    filters = []
    if id_store:
        filters.append(Store.id == id_store)

    # 1) subquery: seleciona filial mais próxima de cada loja
    subq_branches = (
        session.query(
            Store.id,
            Store.name,
            StoreBranch.description.label("branch"),
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
        .filter(*filters)
        .subquery()
    )

    # 2) subquery: apenas rn=1 (filial mais próxima)
    subq_stores = (
        session.query(
            subq_branches.c.id,
            subq_branches.c.name,
            subq_branches.c.branch,
            subq_branches.c.logo,
            subq_branches.c.distance
        )
        .filter(subq_branches.c.rn == 1)
        .order_by(subq_branches.c.id)
        .subquery()
    )

    # 3) cálculo de preço mínimo local e média global
    # média de preço de cada produto em todas as lojas
    subq_avg_price = (
        session.query(
            Offer.id_product.label("pid"),
            func.avg(Offer.price).label("avg_price")
        )
        .group_by(Offer.id_product)
        .subquery()
    )
    # preço mínimo do produto na loja selecionada (ou em cada loja no listing)
    subq_local_min = (
        session.query(
            Offer.id_product.label("pid"),
            func.min(Offer.price).label("min_price")
        )
        .filter(Offer.id_store == subq_stores.c.id)
        .group_by(Offer.id_product)
        .subquery()
    )
    # junta min local e avg global para calcular porcentagem de desconto
    subq_price = (
        session.query(
            subq_local_min.c.pid,
            subq_local_min.c.min_price,
            ((1 - subq_local_min.c.min_price / subq_avg_price.c.avg_price) * 100).label("percentage")
        )
        .join(
            subq_avg_price,
            subq_local_min.c.pid == subq_avg_price.c.pid
        )
        .subquery()
    )

    # 4) filtros de produto (distância, busca, categoria)
    product_filters = [subq_stores.c.distance <= distance_threshold]
    if query:
        product_filters.append(
            func.unaccent(Product.name).ilike(func.unaccent(f"%{query}%"))
        )
    if id_category:
        product_filters.append(Product.id_category == id_category)

    # 5) query final: produtos com menor preço + cálculo de desconto
    products_query = (
        session.query(
            Product,
            Offer,
            subq_price.c.percentage,
            subq_stores.c.name,
            subq_stores.c.branch,
            subq_stores.c.distance,
            subq_stores.c.logo
        )
        .join(Offer, Offer.id_product == Product.id)
        .join(
            subq_price,
            and_(
                Offer.id_product == subq_price.c.pid,
                Offer.price == subq_price.c.min_price
            )
        )
        .join(subq_stores, Offer.id_store == subq_stores.c.id)
        .filter(*product_filters)
        .order_by(desc(subq_price.c.percentage))
        .offset((page - 1) * limit)
        .limit(limit)
    )

    # 6) execução e formatação do resultado
    return [
        {
            "id": prod.id,
            "name": prod.name,
            "expiration_offer": offer.expiration,
            "price": offer.price,
            "percentage": round(percentage),
            "url_image": prod.url_image,
            "store": {
                "id": offer.id_store,
                "name": store,
                "branch": branch,
                "distance": round(distance),
                "logo": url_logo,
            }
        }
        for prod, offer, percentage, store, branch, distance, url_logo in products_query.all()
    ]
