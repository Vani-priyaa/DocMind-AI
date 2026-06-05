"""
PDF Document Management Endpoints for DocMind AI.
Handles upload, metadata, versions, and file downloads.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import shutil
import logging

from app.core import database
from app.core.config import settings
from app.models.all_models import PDFDocument, PDFVersion, PDFChunk, ChatSession
from app.services.pdf_processor import pdf_processor
from app.services.pdf_editor import pdf_editor

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_pdf(
    session_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
):
    """Upload a PDF document, extract content, chunk, and index."""
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Create upload directory
        upload_dir = os.path.join(settings.PDF_UPLOAD_DIR, str(session_id))
        os.makedirs(upload_dir, exist_ok=True)

        # Save file
        original_filename = file.filename
        safe_filename = original_filename.replace(" ", "_")
        file_path = os.path.join(upload_dir, safe_filename)

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # Create document record
        doc = PDFDocument(
            session_id=session_id,
            filename=original_filename,
            original_path=file_path,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Create version 1 directory
        version_dir = os.path.join(upload_dir, f"doc_{doc.id}")
        os.makedirs(version_dir, exist_ok=True)
        version_path = os.path.join(version_dir, "v1.pdf")
        shutil.copy2(file_path, version_path)

        # Extract text and metadata
        extracted = pdf_processor.extract_text_and_metadata(version_path)

        # Update page count
        doc.page_count = extracted["page_count"]

        # Create version 1
        version = PDFVersion(
            document_id=doc.id,
            version_number=1,
            file_path=version_path,
            change_description="Original upload",
        )
        db.add(version)
        db.commit()
        db.refresh(version)

        # Chunk and index
        chunks = pdf_processor.chunk_document(extracted["pages"])
        pdf_processor.index_chunks(db, version.id, chunks)

        # Generate document profile in background
        background_tasks.add_task(
            _generate_profile_background,
            doc_id=doc.id,
            version_id=version.id,
            pages_data=extracted["pages"],
            all_headings=extracted["all_headings"],
        )

        return {
            "id": doc.id,
            "filename": original_filename,
            "page_count": extracted["page_count"],
            "version_id": version.id,
            "version_number": 1,
            "chunks_indexed": len(chunks),
            "status": "uploaded",
            "headings": extracted["all_headings"][:20],
        }

    except Exception as e:
        logger.error(f"PDF upload failed: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_profile_background(
    doc_id: int,
    version_id: int,
    pages_data: list,
    all_headings: list,
):
    """Background task to generate document profile and suggestions."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        profile = await pdf_processor.generate_document_profile(pages_data, all_headings)

        version = db.query(PDFVersion).filter(PDFVersion.id == version_id).first()
        if version:
            version.summary = {
                "executive": profile.get("executive_summary", ""),
                "bullet": profile.get("bullet_summary", ""),
                "technical": profile.get("technical_summary", ""),
            }
            version.suggestions = {
                "topics": profile.get("topics", []),
                "key_terms": profile.get("key_terms", []),
                "suggested_questions": profile.get("suggested_questions", []),
                "headings": all_headings[:30],
            }
            db.commit()
            logger.info(f"Document profile generated for doc {doc_id}, version {version_id}")
    except Exception as e:
        logger.error(f"Profile generation failed: {e}")
    finally:
        db.close()


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(database.get_db)):
    """Get document metadata and latest version info."""
    doc = db.query(PDFDocument).filter(PDFDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    latest_version = db.query(PDFVersion).filter(
        PDFVersion.document_id == doc_id
    ).order_by(PDFVersion.version_number.desc()).first()

    return {
        "id": doc.id,
        "filename": doc.filename,
        "page_count": doc.page_count,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "latest_version": {
            "id": latest_version.id,
            "version_number": latest_version.version_number,
            "change_description": latest_version.change_description,
            "summary": latest_version.summary,
            "created_at": latest_version.created_at.isoformat() if latest_version.created_at else None,
        } if latest_version else None,
    }


@router.get("/{doc_id}/versions")
def get_versions(doc_id: int, db: Session = Depends(database.get_db)):
    """List all versions of a document."""
    versions = db.query(PDFVersion).filter(
        PDFVersion.document_id == doc_id
    ).order_by(PDFVersion.version_number.desc()).all()

    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "change_description": v.change_description,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.get("/{doc_id}/versions/{version_id}/file")
def download_version_file(
    doc_id: int,
    version_id: int,
    db: Session = Depends(database.get_db),
):
    """Download the PDF file for a specific version."""
    version = db.query(PDFVersion).filter(
        PDFVersion.id == version_id,
        PDFVersion.document_id == doc_id,
    ).first()

    if not version or not os.path.exists(version.file_path):
        raise HTTPException(status_code=404, detail="Version file not found")

    return FileResponse(
        version.file_path,
        media_type="application/pdf",
        filename=f"docmind_v{version.version_number}.pdf",
        content_disposition_type="inline",
    )


@router.get("/{doc_id}/pages/{page_num}")
def get_page_text(
    doc_id: int,
    page_num: int,
    db: Session = Depends(database.get_db),
):
    """Get text content of a specific page from the latest version."""
    latest = db.query(PDFVersion).filter(
        PDFVersion.document_id == doc_id
    ).order_by(PDFVersion.version_number.desc()).first()

    if not latest or not os.path.exists(latest.file_path):
        raise HTTPException(status_code=404, detail="Document not found")

    text = pdf_editor.get_page_text(latest.file_path, page_num)
    return {"page_number": page_num, "text": text}


@router.get("/session/{session_id}/documents")
def get_session_documents(session_id: int, db: Session = Depends(database.get_db)):
    """List all PDF documents in a session."""
    docs = db.query(PDFDocument).filter(
        PDFDocument.session_id == session_id
    ).order_by(PDFDocument.created_at.desc()).all()

    result = []
    for doc in docs:
        latest = db.query(PDFVersion).filter(
            PDFVersion.document_id == doc.id
        ).order_by(PDFVersion.version_number.desc()).first()

        result.append({
            "id": doc.id,
            "filename": doc.filename,
            "page_count": doc.page_count,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "latest_version_number": latest.version_number if latest else 0,
            "has_summary": bool(latest and latest.summary),
        })

    return result


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(database.get_db)):
    """Delete a document and all its versions."""
    doc = db.query(PDFDocument).filter(PDFDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete version chunks from ChromaDB
    versions = db.query(PDFVersion).filter(PDFVersion.document_id == doc_id).all()
    for version in versions:
        pdf_processor.delete_version_chunks(version.id, db)

    # Delete the document (cascades to versions, chunks, chat messages, edit previews)
    db.delete(doc)
    db.commit()

    return {"status": "deleted", "id": doc_id}
