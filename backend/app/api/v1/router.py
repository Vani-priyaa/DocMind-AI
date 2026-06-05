from fastapi import APIRouter
from app.api.v1.endpoints import auth, sessions, chat, upload, download, pdf, pdf_chat

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(download.router, prefix="/download", tags=["download"])
api_router.include_router(pdf.router, prefix="/pdf", tags=["pdf"])
api_router.include_router(pdf_chat.router, prefix="/pdf-chat", tags=["pdf-chat"])
