from fastapi import APIRouter

from app.api.routes import items, login, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)


from app.domains.agent.router import router as agent_router
from app.domains.culture.router import router as culture_router
from app.domains.spatial.router import router as spatial_router
from app.domains.inventory.router import router as inventory_router
from app.domains.vision.router import router as vision_router
from app.domains.planner.router import router as planner_router

# if settings.ENVIRONMENT == "local":
#     api_router.include_router(private.router)

# Đăng ký các Domain Router mới (DDD)
api_router.include_router(agent_router, prefix="/agent", tags=["agent"])
api_router.include_router(culture_router, prefix="/culture", tags=["culture"])
api_router.include_router(spatial_router, prefix="/spatial", tags=["spatial"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
api_router.include_router(vision_router, prefix="/vision", tags=["vision"])
api_router.include_router(planner_router, prefix="/planner", tags=["planner"])
