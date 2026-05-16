from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domains.spatial import service, schema

router = APIRouter()

@router.get("/search", response_model=list[schema.PlaceResponse])
def search_places_omni(
    q: str,
    lat: float = Query(None, ge=-90, le=90),
    lon: float = Query(None, ge=-180, le=180),
    db: Session = Depends(get_db)
):
    try:
        return service.search_places_omnisearch(db=db, query_text=q, user_lat=lat, user_lon=lon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

@router.get("/nearby-places", response_model=schema.NearbySearchResponse)
def find_nearby_places(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius: int = Query(2000, ge=0, le=20000),
    db: Session = Depends(get_db)
):
    try:
        places = service.get_nearby_places(db=db, lat=lat, lon=lon, radius_meters=radius)
        return {
            "user_location": {"lat": lat, "lon": lon}, 
            "search_radius_meters": radius, 
            "total_found": len(places),
            "places": places
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

@router.get("/nearby-stores", response_model=schema.NearbyStoreResponse)
def find_nearby_stores(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_m: int = Query(3000, ge=0, le=50000),
    category: str = Query(None),
    min_rating: float = Query(0.0, ge=0.0, le=5.0),
    order_by: str = Query("rating"),
    db: Session = Depends(get_db)
):
    try:
        stores = service.get_nearby_stores(
            db=db, 
            lat=lat, 
            lon=lon, 
            radius_meters=radius_m, 
            category=category, 
            min_rating=min_rating, 
            order_by=order_by
        )
        return {
            "user_location": {"lat": lat, "lon": lon}, 
            "search_radius_meters": radius_m, 
            "total_found": len(stores),
            "stores": stores
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

@router.post("/cluster-stores", response_model=schema.ClusterResponse)
def cluster_and_group_stores(request: schema.ClusterRequest, db: Session = Depends(get_db)):
    """Gom cụm Places & Stores bằng KMeans và ST_DWithin"""
    if not request.place_ids: raise HTTPException(status_code=400, detail="Cần ít nhất 1 place_id")
    try:
        return service.cluster_stores_around_places(db=db, place_ids=request.place_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/route-plan", response_model=schema.RoutePlanResponse)
async def create_optimal_route(request: schema.RoutePlanRequest, db: Session = Depends(get_db)):
    """TSP Greedy Optimization & OSRM Routing"""
    try:
        data = await service.plan_route_osrm(db, request.current_lat, request.current_lon, request.place_ids)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi Routing OSRM: {str(e)}")

@router.get("/places/{place_id}/o2o-context", response_model=schema.O2OContextResponse)
def get_place_o2o_context_api(
    place_id: str,
    radius: int = Query(2000, ge=0, le=20000),
    db: Session = Depends(get_db)
):
    try:
        return service.get_place_o2o_context(db=db, place_id=place_id, radius=radius)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")