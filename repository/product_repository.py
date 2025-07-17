from database.models import Product, Offer, StoreBranch
from sqlalchemy.orm import Session, joinedload
from datetime import date

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
            .options(
                joinedload(Product.offers)
                    .joinedload(Offer.store_branch)
                    .joinedload(StoreBranch.store)
            )
            .all()
    )
    return products