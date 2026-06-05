from fastapi import FastAPI, HTTPException, Request, Form, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import traceback
import os
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging import setup_logging
from app.models import all_models

# Setup Logging
logger = setup_logging()

# Create tables (in prod use alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# --- Legacy routes for backward compatibility ---
from fastapi import Form, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core import database, security
from app.api.v1.endpoints import auth, sessions, chat, upload
from app.models import all_models
from app.services import utils as service_utils

@app.post("/register")
def legacy_register(email: str = Form(...), password: str = Form(...), db: Session = Depends(database.get_db)):
    user = db.query(all_models.User).filter(all_models.User.email == email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = all_models.User(
        email=email, 
        hashed_password=security.get_password_hash(password),
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email}

@app.post("/login")
def legacy_login(email: str = Form(...), password: str = Form(...), db: Session = Depends(database.get_db)):
    user = db.query(all_models.User).filter(all_models.User.email == email).first()
    if not user or not security.verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"id": user.id, "email": user.email}

@app.get("/sessions/{user_id}")
def legacy_get_sessions(user_id: int, db: Session = Depends(database.get_db)):
    sessions_list = db.query(all_models.ChatSession).filter(all_models.ChatSession.user_id == user_id).order_by(all_models.ChatSession.id.desc()).all()
    return sessions_list

@app.post("/sessions")
def legacy_create_session(user_id: int, title: str, db: Session = Depends(database.get_db)):
    session = all_models.ChatSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@app.post("/chat/{session_id}")
async def legacy_chat_wrapper(
    session_id: int, 
    query: str = Form(...), 
    db: Session = Depends(database.get_db)
):
    return await chat.chat_with_data(session_id=session_id, query=query, db=db)

@app.post("/upload/{session_id}")
async def legacy_upload_wrapper(
    session_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(database.get_db)
):
    return await upload.upload_dataset(session_id=session_id, file=file, db=db)

@app.get("/history/{session_id}")
def legacy_get_history(session_id: int, db: Session = Depends(database.get_db)):
    return db.query(all_models.Message).filter(all_models.Message.session_id == session_id).all()

@app.get("/download/{session_id}")
def legacy_download_pdf(session_id: int, db: Session = Depends(database.get_db)):
    session = db.query(all_models.ChatSession).filter(all_models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = db.query(all_models.Message).filter(all_models.Message.session_id == session_id).all()
    pdf_io = service_utils.generate_pdf(session.title, messages)
    headers = {
        "Content-Disposition": f'attachment; filename="analysis_report_{session_id}.pdf"',
        "Access-Control-Expose-Headers": "Content-Disposition",
        "Cache-Control": "no-cache"
    }
    return StreamingResponse(pdf_io, media_type="application/pdf", headers=headers)


@app.get("/health")
def health_check():
    logger.info("Health check requested")
    return {"status": "ok", "app": "DocMind AI", "version": "2.0.0"}
