from fastapi import APIRouter

from app.api.endpoints import auth, pedidos

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(pedidos.router)
