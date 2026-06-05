from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
import os
import shutil

from app.core import database
from app.models.all_models import Dataset
from app.services.ai_orchestrator import orchestrator # To use for summary if needed

router = APIRouter()

import logging
import pandas as pd
import io

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads" 

@router.post("/{session_id}/upload")
async def upload_dataset(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    try:
        # 1. Validate File
        filename = file.filename.lower()
        if not filename.endswith(('.csv', '.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # 2. Save File
        session_dir = os.path.join(UPLOAD_DIR, str(session_id))
        os.makedirs(session_dir, exist_ok=True)
        file_path = os.path.join(session_dir, file.filename)
        
        # Reset file pointer and read for processing
        await file.seek(0)
        contents = await file.read()
        
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
            
        # 3. Extract basic metadata (like old main.py)
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(contents), low_memory=False)
            else:
                df = pd.read_excel(io.BytesIO(contents))
            columns = df.columns.tolist()
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
            columns = []

        # 4. Create Record
        dataset = Dataset(
            session_id=session_id,
            filename=file.filename,
            file_path=file_path,
            columns=columns,
            summary={}
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        # 5. Visualization Generation (Skipped here, now handled by AI on demand)
        visualization = None

        return {
            "filename": file.filename, 
            "id": dataset.id, 
            "status": "uploaded",
            "visualization": visualization
        }
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
