from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core import database
from app.models.all_models import ChatSession, Message, Dataset
from app.services import utils as service_utils
from app.services.ai_orchestrator import orchestrator
import io

router = APIRouter()

@router.get("/dataset/{dataset_id}")
def download_cleaned_dataset(dataset_id: int, db: Session = Depends(database.get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    dfs = orchestrator.get_or_load_dataframes([dataset])
    if dataset.filename not in dfs:
        raise HTTPException(status_code=500, detail="Could not load dataset from memory.")
        
    df = dfs[dataset.filename]
    
    # Export to CSV
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    return StreamingResponse(
        iter([stream.getvalue()]), 
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cleaned_{dataset.filename}"}
    )

@router.get("/session/{session_id}/dataset")
def download_session_dataset(session_id: int, db: Session = Depends(database.get_db)):
    datasets = db.query(Dataset).filter(Dataset.session_id == session_id).order_by(Dataset.id.desc()).all()
    if not datasets:
        raise HTTPException(status_code=404, detail="No datasets uploaded to this session yet.")
        
    dataset = datasets[0] # Get the latest dataset
    dfs = orchestrator.get_or_load_dataframes([dataset])
    df = dfs.get(dataset.filename)
    if df is None:
        raise HTTPException(status_code=500, detail="Could not load dataset from memory.")
        
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    return StreamingResponse(
        iter([stream.getvalue()]), 
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cleaned_{dataset.filename}"}
    )

@router.get("/{session_id}")
def download_session_report(session_id: int, db: Session = Depends(database.get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at).all()
    
    # Generate PDF using the unified visualization utility
    pdf_output = service_utils.generate_pdf(session.title, messages)
    pdf_output.seek(0)
    
    return StreamingResponse(
        pdf_output, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=report_{session_id}.pdf",
                 "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )
