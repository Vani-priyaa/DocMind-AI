from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
import datetime
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="session", cascade="all, delete-orphan")
    pdf_documents = relationship("PDFDocument", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)  # "user", "assistant", "system"
    content = Column(Text)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    filename = Column(String)
    file_path = Column(String)
    columns = Column(JSON)
    summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("ChatSession", back_populates="datasets")


class PDFDocument(Base):
    __tablename__ = "pdf_documents"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String)
    original_path = Column(String)
    page_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ChatSession", back_populates="pdf_documents")
    versions = relationship("PDFVersion", back_populates="document", cascade="all, delete-orphan")
    chat_messages = relationship("PDFChatMessage", back_populates="document", cascade="all, delete-orphan")
    edit_previews = relationship("PDFEditPreview", back_populates="document", cascade="all, delete-orphan")


class PDFVersion(Base):
    __tablename__ = "pdf_versions"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("pdf_documents.id"))
    version_number = Column(Integer)
    file_path = Column(String)
    summary = Column(JSON, nullable=True)        # {"executive": "...", "bullet": "...", "technical": "..."}
    suggestions = Column(JSON, nullable=True)     # {"topics": [...], "suggested_questions": [...], "headings": [...]}
    change_description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("PDFDocument", back_populates="versions")
    chunks = relationship("PDFChunk", back_populates="version", cascade="all, delete-orphan")


class PDFChunk(Base):
    __tablename__ = "pdf_chunks"
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("pdf_versions.id"))
    page_number = Column(Integer)
    heading = Column(String, nullable=True)
    content = Column(Text)

    version = relationship("PDFVersion", back_populates="chunks")


class PDFChatMessage(Base):
    """Chat messages specific to PDF document interactions."""
    __tablename__ = "pdf_chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("pdf_documents.id"))
    role = Column(String)  # "user", "assistant"
    content = Column(Text)
    sources = Column(JSON, nullable=True)     # [{"page_number": 1, "heading": "...", "snippet": "..."}]
    follow_ups = Column(JSON, nullable=True)  # ["question1", "question2"]
    message_type = Column(String, default="chat")  # "chat", "summary", "edit"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("PDFDocument", back_populates="chat_messages")


class PDFEditPreview(Base):
    """Stores pending edit previews before user confirmation."""
    __tablename__ = "pdf_edit_previews"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("pdf_documents.id"))
    version_id = Column(Integer, ForeignKey("pdf_versions.id"))
    command = Column(Text)
    edit_plan = Column(JSON)  # The full edit plan from Gemini
    status = Column(String, default="pending")  # "pending", "applied", "rejected"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("PDFDocument", back_populates="edit_previews")


class AuditLog(Base):
    """Audit log for tracking all operations (scaffolded for RBAC)."""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String)        # "upload", "chat", "edit", "download", "delete"
    resource_type = Column(String)  # "pdf_document", "pdf_version"
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
