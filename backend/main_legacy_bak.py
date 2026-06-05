from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
import io
import os
import json
from typing import List, Optional, Dict
import models, database, utils

# Initialize database
database.init_db()

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REFACTOR: Removed global caches (df_cache, _analyzer_cache) for production isolation.

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_analyzer():
    # In a real production app, we might check a per-user API key here.
    # For now, we use the env var but instantiate fresh to avoid shared state.
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        return None
    return utils.DataAnalyzer(api_key)

async def get_df(file_path: str, filename: str) -> pd.DataFrame:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    def process_df():
        if filename.endswith(".csv"):
            try:
                return pd.read_csv(file_path, low_memory=False, engine='pyarrow')
            except:
                return pd.read_csv(file_path, low_memory=False)
        elif filename.endswith((".xls", ".xlsx")):
            return pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format")

    return await run_in_threadpool(process_df)

@app.post("/register")
def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(email=email, password=password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email}

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or user.password != password:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"id": user.id, "email": user.email}

@app.post("/sessions")
def create_session(user_id: int, title: str, db: Session = Depends(get_db)):
    session = models.ChatSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@app.get("/sessions/{user_id}")
def get_sessions(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.ChatSession).filter(models.ChatSession.user_id == user_id).order_by(models.ChatSession.id.desc()).all()

@app.put("/sessions/{session_id}")
def update_session(session_id: int, title: str = Form(...), db: Session = Depends(get_db)):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = title
    db.commit()
    db.refresh(session)
    return session

@app.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete related data
    db.query(models.Message).filter(models.Message.session_id == session_id).delete()
    db.query(models.Dataset).filter(models.Dataset.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"status": "deleted"}

def save_file_to_disk(file_path: str, contents: bytes):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(contents)

@app.post("/upload/{session_id}")
async def upload_file(
    session_id: int, 
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    try:
        if not file.size:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
            
        # Fast processing
        def process_df(file_obj, filename):
            file_obj.seek(0)
            if filename.endswith(".csv"):
                # Use pyarrow engine if available, else default
                try:
                    return pd.read_csv(file_obj, low_memory=False, engine='pyarrow')
                except:
                    file_obj.seek(0)
                    return pd.read_csv(file_obj, low_memory=False)
            elif filename.endswith((".xls", ".xlsx")):
                return pd.read_excel(file_obj)
            else:
                raise ValueError("Unsupported file format")

        df = await run_in_threadpool(process_df, file.file, file.filename)
        
        # Define file path
        file_path = os.path.join(UPLOAD_DIR, str(session_id), file.filename)
        
        # Read contents for background save
        file.file.seek(0)
        contents = await file.read()
        
        # Save to disk and update summary in background
        def background_processing(ds_id: int, f_path: str, f_contents: bytes):
            save_file_to_disk(f_path, f_contents)
            db_bg = database.SessionLocal()
            try:
                ds = db_bg.query(models.Dataset).filter(models.Dataset.id == ds_id).first()
                if ds:
                    summary = utils.get_df_summary(df)
                    ds.summary = summary
                    db_bg.commit()
            except Exception as e:
                print(f"Error in background processing: {e}")
            finally:
                db_bg.close()

        # Create record
        dataset = models.Dataset(
            session_id=session_id,
            filename=file.filename,
            file_path=file_path,
            columns=df.columns.tolist(),
            summary=None
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        background_tasks.add_task(background_processing, dataset.id, file_path, contents)

        return {"filename": file.filename, "status": "processing"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/chat/{session_id}")
async def chat(session_id: int, query: str = Form(...), db: Session = Depends(get_db)):
    # 1. Get history
    messages = db.query(models.Message).filter(models.Message.session_id == session_id).all()
    history = [{"role": m.role, "content": m.content} for m in messages]

    # 2. Get datasets
    datasets = db.query(models.Dataset).filter(models.Dataset.session_id == session_id).order_by(models.Dataset.id.asc()).all()
    
    async def load_all_dfs(datasets_list):
        dfs = {}
        for d in datasets_list:
            try:
                dfs[d.filename] = await get_df(d.file_path, d.filename)
            except Exception as e:
                print(f"Error loading {d.filename}: {e}")
        return dfs

    dfs = await load_all_dfs(datasets)

    # 3. Analyze
    analyzer = get_analyzer()
    if not analyzer:
        return {
            "explanation": "Configuration Error: NVIDIA_API_KEY is missing in backend/.env. Please add your API key to proceed.",
            "visualization": None,
            "code": None
        }
    
    # Extract summaries to pass to analyzer
    summaries = {d.filename: d.summary for d in datasets if d.summary}
    
    try:
        result = await analyzer.analyze_data(query, dfs, history, summaries)
    except Exception as e:
        print(f"Analysis Exception: {e}")
        return {
            "explanation": f"System Error: {str(e)}",
            "visualization": None,
            "code": None
        }

    # 4. Save messages
    user_msg = models.Message(session_id=session_id, role="user", content=query)
    asst_msg = models.Message(
        session_id=session_id, 
        role="assistant", 
        content=result["explanation"],
        data=result.get("visualization")
    )
    db.add(user_msg)
    db.add(asst_msg)
    db.commit()

    return {
        "explanation": result["explanation"],
        "visualization": result.get("visualization"),
        "code": result.get("code")
    }

@app.get("/history/{session_id}")
def get_history(session_id: int, db: Session = Depends(get_db)):
    return db.query(models.Message).filter(models.Message.session_id == session_id).all()

@app.get("/download/{session_id}")
def download_pdf(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(models.Message).filter(models.Message.session_id == session_id).all()
    print(f"Generating PDF for session {session_id} with {len(messages)} messages")
    pdf_io = utils.generate_pdf(session.title, messages)
    
    headers = {
        "Content-Disposition": f'attachment; filename="analysis_report_{session_id}.pdf"',
        "Access-Control-Expose-Headers": "Content-Disposition",
        "Cache-Control": "no-cache"
    }
    
    return StreamingResponse(
        pdf_io,
        media_type="application/pdf",
        headers=headers
    )

if __name__ == "__main__":
    import uvicorn
    database.init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
