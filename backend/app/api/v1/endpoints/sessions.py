from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List

from app.core import database
from app.models.all_models import ChatSession as ChatSessionModel
from app.schemas.session import ChatSession, ChatSessionCreate

router = APIRouter()

@router.post("/", response_model=ChatSession)
def create_session(
    session_in: ChatSessionCreate, 
    user_id: int, # In prod, extract from current_user
    db: Session = Depends(database.get_db)
):
    session = ChatSessionModel(user_id=user_id, title=session_in.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/", response_model=List[ChatSession])
def read_sessions(
    user_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db)
):
    sessions = db.query(ChatSessionModel).filter(ChatSessionModel.user_id == user_id).offset(skip).limit(limit).all()
    return sessions

@router.get("/{session_id}", response_model=ChatSession)
def read_session(
    session_id: int, 
    db: Session = Depends(database.get_db)
):
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(database.get_db)):
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"ok": True}
@router.put("/{session_id}", response_model=ChatSession)
def update_session(
    session_id: int, 
    title: str = Form(...),
    db: Session = Depends(database.get_db)
):
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.title = title
    db.commit()
    db.refresh(session)
    return session
