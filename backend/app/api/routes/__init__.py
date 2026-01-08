from fastapi import APIRouter
from app.api.routes import upload, extract, chat, export

api_router = APIRouter()

# Include all route modules
api_router.include_router(upload.router)
api_router.include_router(extract.router)
api_router.include_router(chat.router)
api_router.include_router(export.router)
