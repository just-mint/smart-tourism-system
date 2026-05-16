from geoalchemy2.elements import WKTElement
from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.domains.culture.model import Place
from app.domains.inventory.model import Inventory, Product, Store
from app.models import User, UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

    seed_demo_o2o_data(session)


def seed_demo_o2o_data(session: Session) -> None:
    existing_place = (
        session.query(Place).filter(Place.place_id == "demo-hoan-kiem").first()
    )
    if existing_place:
        demo_places = session.query(Place).filter(Place.place_id.like("demo-%")).all()
        for place in demo_places:
            if place.lat is not None and place.lon is not None:
                place.geom = WKTElement(f"POINT({place.lon} {place.lat})", srid=4326)

        demo_stores = session.query(Store).filter(Store.place_id.like("demo-%")).all()
        for store in demo_stores:
            store.category = "shopping"
            if store.lat is not None and store.lon is not None:
                store.geom = WKTElement(f"POINT({store.lon} {store.lat})", srid=4326)
        session.commit()
        return

    places = [
        Place(
            place_id="demo-hoan-kiem",
            place_type="attraction",
            name="Hoan Kiem Lake",
            category="heritage",
            address="Hoan Kiem, Hanoi",
            lat=21.0285,
            lon=105.8542,
            phone="02438253928",
            rating=4.7,
            review_count=1280,
            image_url="https://images.unsplash.com/photo-1559592413-7ceecea18501?auto=format&fit=crop&w=1200",
            geom=WKTElement("POINT(105.8542 21.0285)", srid=4326),
        ),
        Place(
            place_id="demo-temple-literature",
            place_type="attraction",
            name="Temple of Literature",
            category="culture",
            address="58 Quoc Tu Giam, Hanoi",
            lat=21.0277,
            lon=105.8355,
            phone="02438452917",
            rating=4.8,
            review_count=920,
            image_url="https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200",
            geom=WKTElement("POINT(105.8355 21.0277)", srid=4326),
        ),
        Place(
            place_id="demo-old-quarter",
            place_type="district",
            name="Hanoi Old Quarter",
            category="shopping",
            address="Hoan Kiem, Hanoi",
            lat=21.0338,
            lon=105.8500,
            phone="02439287429",
            rating=4.6,
            review_count=2100,
            image_url="https://images.unsplash.com/photo-1504457047772-27faf1c00561?auto=format&fit=crop&w=1200",
            geom=WKTElement("POINT(105.8500 21.0338)", srid=4326),
        ),
    ]
    session.add_all(places)
    session.flush()

    products = [
        Product(
            name="Lotus Silk Scarf",
            description="Locally made silk scarf inspired by Hanoi lotus motifs.",
            price=250000,
            original_price=320000,
            image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=800",
            size="Free",
            color="Ivory",
            tags="silk,local,heritage",
        ),
        Product(
            name="Bat Trang Ceramic Cup",
            description="Handmade ceramic cup from Bat Trang craft village.",
            price=180000,
            original_price=220000,
            image_url="https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=800",
            size="M",
            color="Blue",
            tags="ceramic,souvenir,craft",
        ),
        Product(
            name="Vietnam Heritage T-Shirt",
            description="Soft cotton tee with a minimal heritage print.",
            price=199000,
            original_price=249000,
            image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=800",
            size="M",
            color="White",
            tags="fashion,travel,o2o",
        ),
        Product(
            name="Robusta Coffee Gift Box",
            description="Vietnamese robusta coffee gift set for travelers.",
            price=320000,
            original_price=390000,
            image_url="https://images.unsplash.com/photo-1559056199-641a0ac8b55e?auto=format&fit=crop&w=800",
            size="500g",
            color="Brown",
            tags="coffee,gift,local",
        ),
    ]
    session.add_all(products)
    session.flush()

    stores = [
        Store(
            place_id="demo-hoan-kiem",
            name="Hoan Kiem O2O Hub",
            category="shopping",
            address="12 Dinh Tien Hoang, Hanoi",
            lat=21.0290,
            lon=105.8538,
            phone="0901000001",
            rating=4.7,
            geom=WKTElement("POINT(105.8538 21.0290)", srid=4326),
        ),
        Store(
            place_id="demo-temple-literature",
            name="Temple Heritage Gifts",
            category="shopping",
            address="60 Quoc Tu Giam, Hanoi",
            lat=21.0279,
            lon=105.8359,
            phone="0901000002",
            rating=4.8,
            geom=WKTElement("POINT(105.8359 21.0279)", srid=4326),
        ),
        Store(
            place_id="demo-old-quarter",
            name="Old Quarter Local Market",
            category="shopping",
            address="Hang Gai, Hanoi",
            lat=21.0332,
            lon=105.8494,
            phone="0901000003",
            rating=4.6,
            geom=WKTElement("POINT(105.8494 21.0332)", srid=4326),
        ),
    ]
    session.add_all(stores)
    session.flush()

    inventory_rows = []
    for store_index, store in enumerate(stores):
        for product_index, product in enumerate(products):
            inventory_rows.append(
                Inventory(
                    store_id=store.store_id,
                    product_id=product.product_id,
                    stock=20 + store_index * 5 + product_index,
                    locked_stock=0,
                    price_override=product.price - store_index * 10000,
                )
            )
    session.add_all(inventory_rows)
    session.commit()
