from fastapi import APIRouter

from app.api.v1 import (
    auth,
    chat,
    documents,
    evaluation,
    evaluation_datasets,
    health,
    me,
    search,
    settings,
    usage,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(me.router, tags=["identity"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(evaluation.router, tags=["evaluation"])
api_router.include_router(evaluation_datasets.router, tags=["evaluation"])
api_router.include_router(usage.router, tags=["usage"])
api_router.include_router(settings.router, tags=["settings"])
