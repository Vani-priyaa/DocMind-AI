from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Any
import pandas as pd
import os

from app.core import database, config
from app.models.all_models import ChatSession, Message, Dataset
from app.services.ai_orchestrator import orchestrator
from app.services import mail, utils as service_utils
from app.schemas.user import User
from app.schemas.session import ChatRequest
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to get current user would go here (omitted for brevity, assume protected)

@router.post("/{session_id}/send")
async def chat_with_data(
    session_id: int, 
    request: ChatRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db)
):
    query = request.query
    logger.info(f"Received Query: '{query}' for Session: {session_id}")
    # 1. Fetch Session & History
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = db.query(Message).filter(Message.session_id == session_id).all()
    history = [{"role": m.role, "content": m.content} for m in messages]
    
    # 2. Load Datasets
    # Uses caching to prevent re-reading large files on every request
    datasets = db.query(Dataset).filter(Dataset.session_id == session_id).order_by(Dataset.id.asc()).all()
    dfs = orchestrator.get_or_load_dataframes(datasets)

    # 3. Analyze
    result = await orchestrator.analyze_data(query, dfs, history)
    
    # 4. Save Interaction
    user_msg = Message(session_id=session_id, role="user", content=query)
    asst_msg = Message(
        session_id=session_id, 
        role="assistant", 
        content=result.get("explanation", "Error"),
        data=result.get("visualization")
    )
    db.add(user_msg)
    db.add(asst_msg)
    db.commit()

    # 5. Handle Email Forwarding
    recipient_email = result.get("email_to_forward")
    if recipient_email and "@" in recipient_email:
        background_tasks.add_task(
            handle_email_forwarding,
            session_id=session_id,
            recipient_email=recipient_email,
            db_session=db
        )
    
    return result

async def handle_email_forwarding(session_id: int, recipient_email: str, db_session: Session):
    try:
        session = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
        messages = db_session.query(Message).filter(Message.session_id == session_id).all()
        
        # Generate PDF
        pdf_io = service_utils.generate_pdf(session.title, messages)
        pdf_content = pdf_io.getvalue()
        
        mail.send_chat_summary_email(
            recipient_email=recipient_email,
            subject=f"Chat Summary: {session.title}",
            body=f"Hello,\n\nPlease find attached the summary of your data analysis session: '{session.title}'.\n\nBest regards,\nCDA Team",
            pdf_content=pdf_content,
            filename=f"Analysis_Summary_{session_id}.pdf"
        )
    except Exception as e:
        logger.error(f"Error in background email task: {e}")

@router.get("/{session_id}/history")
def get_history(session_id: int, db: Session = Depends(database.get_db)):
    # Assuming Message schema is compatible or just returning ORM list
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()
    return messages
