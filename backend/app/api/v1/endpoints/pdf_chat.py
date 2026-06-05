"""
PDF Chat & AI Interaction Endpoints for DocMind AI.
Handles RAG Q&A, summarization, editing, and autocomplete.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.core import database
from app.models.all_models import PDFDocument, PDFVersion, PDFChatMessage
from app.services.rag_engine import rag_engine

router = APIRouter()
logger = logging.getLogger(__name__)


def handle_gemini_error(e: Exception, context_msg: str):
    err_msg = str(e)
    # Check for Gemini API key suspended / invalid / 403 errors
    if "suspended" in err_msg.lower() or "api_key" in err_msg.lower() or "api key" in err_msg.lower() or "403" in err_msg:
        raise HTTPException(
            status_code=403,
            detail="The Gemini API key is suspended or invalid. Please configure a valid GEMINI_API_KEY in backend/.env."
        )
    raise HTTPException(status_code=500, detail=f"{context_msg}: {err_msg}")



# --- Request Schemas ---

class AskRequest(BaseModel):
    query: str

class SummarizeRequest(BaseModel):
    mode: str = "executive"  # executive, bullet, technical
    pages: Optional[List[int]] = None

class EditRequest(BaseModel):
    command: str

class ConfirmEditRequest(BaseModel):
    preview_id: int


# --- Endpoints ---

@router.post("/{doc_id}/ask")
async def ask_question(
    doc_id: int,
    request: AskRequest,
    db: Session = Depends(database.get_db),
):
    """RAG-powered Q&A with citations and follow-up suggestions."""
    doc = db.query(PDFDocument).filter(PDFDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        result = await rag_engine.answer_question(
            query=request.query,
            document_id=doc_id,
            db=db,
        )

        # Save messages
        user_msg = PDFChatMessage(
            document_id=doc_id,
            role="user",
            content=request.query,
            message_type="chat",
        )
        assistant_msg = PDFChatMessage(
            document_id=doc_id,
            role="assistant",
            content=result.get("answer", ""),
            sources=result.get("sources", []),
            follow_ups=result.get("follow_ups", []),
            message_type="chat",
        )
        db.add(user_msg)
        db.add(assistant_msg)
        db.commit()

        return result

    except Exception as e:
        logger.error(f"Question answering failed: {e}", exc_info=True)
        handle_gemini_error(e, "Question answering failed")



@router.post("/{doc_id}/summarize")
async def summarize_document(
    doc_id: int,
    request: SummarizeRequest,
    db: Session = Depends(database.get_db),
):
    """Summarize the document or specific pages."""
    doc = db.query(PDFDocument).filter(PDFDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        result = await rag_engine.summarize_document(
            document_id=doc_id,
            db=db,
            mode=request.mode,
            pages=request.pages,
        )

        # Save as chat message
        user_msg = PDFChatMessage(
            document_id=doc_id,
            role="user",
            content=f"Summarize ({request.mode})" + (f" pages {request.pages}" if request.pages else ""),
            message_type="summary",
        )
        assistant_msg = PDFChatMessage(
            document_id=doc_id,
            role="assistant",
            content=result.get("summary", ""),
            sources=result.get("sources", []),
            message_type="summary",
        )
        db.add(user_msg)
        db.add(assistant_msg)
        db.commit()

        return result

    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        handle_gemini_error(e, "Summarization failed")



@router.post("/{doc_id}/edit")
async def propose_edit(
    doc_id: int,
    request: EditRequest,
    db: Session = Depends(database.get_db),
):
    """Process a natural language edit command and return a preview."""
    doc = db.query(PDFDocument).filter(PDFDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        result = await rag_engine.process_edit_command(
            command=request.command,
            document_id=doc_id,
            db=db,
        )

        # Save edit command as chat message
        user_msg = PDFChatMessage(
            document_id=doc_id,
            role="user",
            content=request.command,
            message_type="edit",
        )
        assistant_msg = PDFChatMessage(
            document_id=doc_id,
            role="assistant",
            content=f"Edit Preview: {result.get('preview_summary', result.get('description', ''))}",
            sources=[],
            message_type="edit",
        )
        db.add(user_msg)
        db.add(assistant_msg)
        db.commit()

        return result

    except Exception as e:
        logger.error(f"Edit command failed: {e}", exc_info=True)
        handle_gemini_error(e, "Edit command failed")



@router.post("/{doc_id}/edit/confirm")
async def confirm_edit(
    doc_id: int,
    request: ConfirmEditRequest,
    db: Session = Depends(database.get_db),
):
    """Confirm and apply an edit preview."""
    doc = db.query(PDFDocument).filter(PDFDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        result = await rag_engine.apply_edit(
            preview_id=request.preview_id,
            document_id=doc_id,
            db=db,
        )

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        # Save confirmation message
        msg = PDFChatMessage(
            document_id=doc_id,
            role="assistant",
            content=f"✅ Edit applied! Created version {result.get('version_number', '?')}. {result.get('description', '')}",
            message_type="edit",
        )
        db.add(msg)
        db.commit()

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Edit confirmation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{doc_id}/suggestions")
async def get_suggestions(
    doc_id: int,
    q: str = Query("", min_length=0),
    db: Session = Depends(database.get_db),
):
    """Get autocomplete suggestions for the chat input."""
    doc = db.query(PDFDocument).filter(PDFDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # If no query, return stored suggestions
    if not q or len(q) < 2:
        version = db.query(PDFVersion).filter(
            PDFVersion.document_id == doc_id
        ).order_by(PDFVersion.version_number.desc()).first()

        if version and version.suggestions:
            suggestions_data = version.suggestions
            if isinstance(suggestions_data, str):
                import json
                try:
                    suggestions_data = json.loads(suggestions_data)
                except:
                    suggestions_data = {}
            return {"suggestions": suggestions_data.get("suggested_questions", [])[:8]}
        return {"suggestions": []}

    try:
        suggestions = await rag_engine.get_autocomplete_suggestions(
            partial_query=q,
            document_id=doc_id,
            db=db,
        )
        return {"suggestions": suggestions}

    except Exception as e:
        logger.error(f"Autocomplete failed: {e}")
        return {"suggestions": []}


@router.get("/{doc_id}/history")
def get_chat_history(
    doc_id: int,
    db: Session = Depends(database.get_db),
):
    """Get chat history for a document."""
    messages = db.query(PDFChatMessage).filter(
        PDFChatMessage.document_id == doc_id
    ).order_by(PDFChatMessage.created_at.asc()).all()

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "follow_ups": m.follow_ups,
            "message_type": m.message_type,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.get("/{doc_id}/profile")
def get_document_profile(
    doc_id: int,
    db: Session = Depends(database.get_db),
):
    """Get the document's generated profile (summaries, topics, suggestions)."""
    version = db.query(PDFVersion).filter(
        PDFVersion.document_id == doc_id
    ).order_by(PDFVersion.version_number.desc()).first()

    if not version:
        raise HTTPException(status_code=404, detail="Document version not found")

    return {
        "summary": version.summary,
        "suggestions": version.suggestions,
        "version_number": version.version_number,
    }
