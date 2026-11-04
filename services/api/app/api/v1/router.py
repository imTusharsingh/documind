from fastapi import APIRouter

from app.api.v1 import health, me

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(me.router, tags=["identity"])
