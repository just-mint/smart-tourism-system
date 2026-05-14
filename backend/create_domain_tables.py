from app.db.session import engine, Base
# Import all domain models so they are registered with Base
from app.domains.vision.model import VisionTask, VirtualCloset
from app.domains.inventory.model import Store, Product
from app.domains.culture.model import Place, Review

print("Creating domain tables...")
Base.metadata.create_all(bind=engine)
print("Done!")
