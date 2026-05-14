from sqlalchemy import Column, DateTime, Integer, String, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
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
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    author_name = Column(String(100))
    rating = Column(Integer)
    text = Column(Text)
    time_posted = Column(String(100))
    status = Column(String(20), nullable=False, default="pending", index=True)
    report_count = Column(Integer, nullable=False, default=0)
    report_reason = Column(Text, nullable=True)
    reported_at = Column(DateTime(timezone=True), nullable=True)
    moderated_by = Column(UUID(as_uuid=True), nullable=True)
    moderated_at = Column(DateTime(timezone=True), nullable=True)
    moderation_note = Column(Text, nullable=True)
