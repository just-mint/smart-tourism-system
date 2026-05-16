from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, Column, Integer, Numeric, String, Text

from app.db.session import Base


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    place_id = Column(String(50), unique=True, index=True)
    place_type = Column(String(50))
    name = Column(String(255))
    category = Column(String(100), index=True)
    address = Column(Text)
    lat = Column(Numeric)
    lon = Column(Numeric)
    geom = Column(Geometry(geometry_type='POINT', srid=4326))

    # Missing columns appended to match travel_app
    phone = Column(String(50), nullable=True)
    rating = Column(Numeric(3,1), nullable=True)
    review_count = Column(Integer, nullable=True)
    image_url = Column(Text, nullable=True)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    place_id = Column(String(50), index=True)
    author_name = Column(String(100))
    rating = Column(Integer)
    text = Column(Text)
    time_posted = Column(String(100))

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )
