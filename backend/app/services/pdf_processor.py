"""
Enhanced PDF Processor for DocMind AI.
Handles extraction, semantic chunking, indexing, and suggestion generation.
"""
import fitz  # PyMuPDF
import pdfplumber
import os
import re
import logging
import json
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.models.all_models import PDFDocument, PDFVersion, PDFChunk
from app.core.config import settings
from app.services.gemini_client import gemini_client

logger = logging.getLogger(__name__)

# ChromaDB initialization
CHROMA_AVAILABLE = False
chroma_client = None
default_ef = None

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_DIR = settings.CHROMA_DB_DIR
    os.makedirs(CHROMA_DIR, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    CHROMA_AVAILABLE = True
    logger.info(f"ChromaDB initialized at {CHROMA_DIR}")
except Exception as e:
    logger.warning(f"ChromaDB initialization failed: {e}. Falling back to SQLite retrieval.")


class PDFProcessor:
    """Handles PDF text extraction, semantic chunking, vector indexing, and content profiling."""

    def extract_text_and_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts text, headings, tables, and metadata from a PDF.
        Returns structured data with page-level content and document-level metadata.
        """
        pages_data = []
        all_headings = []
        total_text = ""

        # Extract text and headings using PyMuPDF
        doc = fitz.open(file_path)
        page_count = len(doc)

        # Extract tables using pdfplumber
        tables_by_page = {}
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    extracted_tables = page.extract_tables()
                    if extracted_tables:
                        tables_by_page[page_idx] = extracted_tables
        except Exception as e:
            logger.error(f"pdfplumber table extraction failed: {e}")

        for page_idx in range(page_count):
            page = doc[page_idx]
            text = page.get_text()
            total_text += text

            # Enhanced heading extraction using font size analysis
            headings = []
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    line_text = ""
                    max_font_size = 0
                    is_bold = False
                    
                    for span in line["spans"]:
                        line_text += span["text"]
                        max_font_size = max(max_font_size, span["size"])
                        if "bold" in span.get("font", "").lower() or "Bold" in span.get("font", ""):
                            is_bold = True

                    line_text = line_text.strip()
                    
                    # Classify as heading if: larger font, bold, short text, or matches patterns
                    if line_text and len(line_text) > 2 and len(line_text) < 150:
                        is_heading = (
                            max_font_size > 13 or
                            is_bold or
                            line_text.isupper() or
                            re.match(r'^(?:Chapter|Section|Module|Part|Article)\s+\d+', line_text, re.IGNORECASE) or
                            re.match(r'^\d+\.\s+\w', line_text)  # Numbered headings like "1. Introduction"
                        )
                        if is_heading:
                            headings.append({
                                "text": line_text,
                                "font_size": max_font_size,
                                "is_bold": is_bold,
                                "page": page_idx + 1
                            })
                            all_headings.append(line_text)

            # Format tables as markdown
            page_tables = tables_by_page.get(page_idx, [])
            formatted_tables = ""
            for table in page_tables:
                if not table or not table[0]:
                    continue
                formatted_tables += "\n\n| " + " | ".join([str(cell or "").replace("\n", " ") for cell in table[0]]) + " |\n"
                formatted_tables += "| " + " | ".join(["---" for _ in table[0]]) + " |\n"
                for row in table[1:]:
                    formatted_tables += "| " + " | ".join([str(cell or "").replace("\n", " ") for cell in row]) + " |\n"

            full_text = text
            if formatted_tables:
                full_text += "\n\nTable Data:\n" + formatted_tables

            pages_data.append({
                "page": page_idx + 1,
                "text": text,
                "full_search_text": full_text,
                "headings": headings,
                "tables": page_tables
            })

        doc.close()

        return {
            "pages": pages_data,
            "page_count": page_count,
            "all_headings": all_headings,
            "total_chars": len(total_text),
        }

    def chunk_document(
        self,
        pages_data: List[Dict[str, Any]],
        max_chunk_size: int = 600,
        overlap: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Semantic chunking: splits by headings and sections, falling back to sliding window.
        Keeps page references for citation tracking.
        """
        chunks = []

        for page in pages_data:
            page_num = page["page"]
            text = page["full_search_text"]
            headings = page.get("headings", [])
            
            if not text.strip():
                continue

            # Try to split by headings/sections first
            if headings:
                heading_texts = [h["text"] if isinstance(h, dict) else h for h in headings]
                sections = self._split_by_headings(text, heading_texts)
                
                for section_heading, section_text in sections:
                    if not section_text.strip():
                        continue
                    # If section is small enough, keep as one chunk
                    if len(section_text.split()) <= max_chunk_size:
                        chunks.append({
                            "page_number": page_num,
                            "heading": section_heading,
                            "content": section_text.strip()
                        })
                    else:
                        # Sliding window within section
                        sub_chunks = self._sliding_window(section_text, max_chunk_size, overlap)
                        for sc in sub_chunks:
                            chunks.append({
                                "page_number": page_num,
                                "heading": section_heading,
                                "content": sc
                            })
            else:
                # No headings — pure sliding window
                primary_heading = f"Page {page_num}"
                sub_chunks = self._sliding_window(text, max_chunk_size, overlap)
                for sc in sub_chunks:
                    chunks.append({
                        "page_number": page_num,
                        "heading": primary_heading,
                        "content": sc
                    })

        return chunks

    def _split_by_headings(self, text: str, headings: List[str]) -> List[Tuple[str, str]]:
        """Split text by heading boundaries."""
        sections = []
        remaining = text
        
        for i, heading in enumerate(headings):
            idx = remaining.find(heading)
            if idx == -1:
                continue
            
            # Content before this heading
            before = remaining[:idx].strip()
            if before and i == 0:
                sections.append((f"Introduction", before))
            
            # Find next heading to determine section end
            remaining = remaining[idx:]
            next_idx = len(remaining)
            for next_heading in headings[i + 1:]:
                ni = remaining.find(next_heading, len(heading))
                if ni > 0:
                    next_idx = ni
                    break
            
            section_text = remaining[:next_idx]
            sections.append((heading, section_text))
            remaining = remaining[next_idx:]

        # Any leftover text
        if remaining.strip() and not sections:
            sections.append(("Content", remaining.strip()))
        elif remaining.strip():
            sections.append((sections[-1][0] if sections else "Content", remaining.strip()))

        return sections if sections else [("Content", text)]

    def _sliding_window(self, text: str, max_size: int, overlap: int) -> List[str]:
        """Sliding window chunking with word boundaries."""
        words = text.split()
        if not words:
            return []
        
        chunks = []
        idx = 0
        while idx < len(words):
            chunk_words = words[idx:idx + max_size]
            chunks.append(" ".join(chunk_words))
            idx += max_size - overlap
            if idx >= len(words):
                break
        
        return chunks

    def index_chunks(self, db: Session, version_id: int, chunks: List[Dict[str, Any]]):
        """Save chunks to DB and index in ChromaDB for vector search."""
        # Save to SQLAlchemy
        db_chunks = []
        for c in chunks:
            db_chunk = PDFChunk(
                version_id=version_id,
                page_number=c["page_number"],
                heading=c["heading"],
                content=c["content"]
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)
        db.commit()

        # Index in ChromaDB
        if CHROMA_AVAILABLE and chroma_client:
            try:
                collection = chroma_client.get_or_create_collection(
                    name="docmind_chunks",
                    embedding_function=default_ef
                )

                # Batch add
                ids = [f"v{version_id}_chunk_{db_chunk.id}" for db_chunk in db_chunks]
                documents = [c["content"] for c in chunks]
                metadatas = [{
                    "version_id": version_id,
                    "page_number": c["page_number"],
                    "heading": c["heading"] or ""
                } for c in chunks]

                # ChromaDB has a batch limit, process in batches of 100
                batch_size = 100
                for i in range(0, len(ids), batch_size):
                    collection.add(
                        ids=ids[i:i+batch_size],
                        documents=documents[i:i+batch_size],
                        metadatas=metadatas[i:i+batch_size]
                    )

                logger.info(f"Indexed {len(chunks)} chunks in ChromaDB for version {version_id}")
            except Exception as e:
                logger.error(f"ChromaDB indexing failed: {e}")

    def search_chunks(
        self,
        version_id: int,
        query: str,
        limit: int = 5,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks using vector similarity (ChromaDB) or keyword fallback.
        """
        if CHROMA_AVAILABLE and chroma_client:
            try:
                collection = chroma_client.get_or_create_collection(
                    name="docmind_chunks",
                    embedding_function=default_ef
                )

                results = collection.query(
                    query_texts=[query],
                    where={"version_id": version_id},
                    n_results=limit
                )

                if results and results["documents"] and len(results["documents"][0]) > 0:
                    retrieved = []
                    for i in range(len(results["documents"][0])):
                        retrieved.append({
                            "content": results["documents"][0][i],
                            "page_number": results["metadatas"][0][i]["page_number"],
                            "heading": results["metadatas"][0][i]["heading"],
                            "score": results["distances"][0][i] if results.get("distances") else 0
                        })
                    return retrieved
            except Exception as e:
                logger.error(f"ChromaDB search failed: {e}")

        # Fallback: keyword scoring on SQLite
        return self._keyword_search(version_id, query, limit, db)

    def _keyword_search(
        self,
        version_id: int,
        query: str,
        limit: int,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Fallback keyword-based search when ChromaDB is unavailable."""
        close_db = False
        if db is None:
            from app.core.database import SessionLocal
            db = SessionLocal()
            close_db = True

        try:
            chunks = db.query(PDFChunk).filter(PDFChunk.version_id == version_id).all()
            query_words = set(re.findall(r'\w+', query.lower()))
            
            scored = []
            for chunk in chunks:
                chunk_words_set = set(re.findall(r'\w+', chunk.content.lower()))
                # Score = overlap count + bonus for exact phrase matches
                score = len(query_words & chunk_words_set)
                if query.lower() in chunk.content.lower():
                    score += 10  # Bonus for exact match
                if score > 0:
                    scored.append((score, chunk))

            scored.sort(key=lambda x: x[0], reverse=True)

            results = []
            for score, chunk in scored[:limit]:
                results.append({
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "heading": chunk.heading,
                    "score": score
                })

            # If no matches, return first chunks as context
            if not results and chunks:
                for chunk in chunks[:limit]:
                    results.append({
                        "content": chunk.content,
                        "page_number": chunk.page_number,
                        "heading": chunk.heading,
                        "score": 0
                    })

            return results
        finally:
            if close_db:
                db.close()

    async def generate_document_profile(
        self,
        pages_data: List[Dict[str, Any]],
        all_headings: List[str]
    ) -> Dict[str, Any]:
        """
        Generate document summaries, topics, and autocomplete suggestions using Gemini.
        """
        # Build sample text from first few pages
        sample_text = ""
        for p in pages_data[:7]:
            sample_text += f"\n--- PAGE {p['page']} ---\n{p['text'][:1200]}"

        prompt = f"""Analyze this document and generate a comprehensive profile.

DOCUMENT HEADINGS: {', '.join(all_headings[:30])}

DOCUMENT SAMPLE:
{sample_text[:6000]}

Return a JSON object with:
{{
    "executive_summary": "2-3 paragraph executive summary",
    "bullet_summary": "Bullet-point key topics summary (use \\n- for bullets)",
    "technical_summary": "Technical details summary",
    "topics": ["topic1", "topic2", ...],
    "key_terms": ["term1", "term2", ...],
    "suggested_questions": [
        "What is the main purpose of this document?",
        "How do I configure the system?",
        ... (generate 25 relevant questions grounded in the content)
    ]
}}

The questions MUST be grounded in the document's actual content."""

        try:
            result = await gemini_client.generate_json(
                prompt=prompt,
                temperature=0.2,
                max_tokens=4096,
            )
            if result:
                return result
        except Exception as e:
            err_msg = str(e)
            if "suspended" in err_msg.lower() or "api_key" in err_msg.lower() or "api key" in err_msg.lower() or "403" in err_msg:
                logger.error("Document profiling failed: The Gemini API key is suspended or invalid. Please configure a valid GEMINI_API_KEY in backend/.env.")
            else:
                logger.error(f"Document profiling failed: {e}")

        # Fallback
        return {
            "executive_summary": "Document uploaded successfully. Ask questions in the chat to learn about its contents.",
            "bullet_summary": "- Document uploaded\n- Text extraction complete\n- Ready for Q&A",
            "technical_summary": "Standard PDF document processed.",
            "topics": [h for h in all_headings[:10]],
            "key_terms": [],
            "suggested_questions": [
                "What is the main topic of this document?",
                "Can you summarize the key points?",
                "What are the main sections?",
                "What conclusions are drawn?",
                "What recommendations are made?"
            ]
        }

    def delete_version_chunks(self, version_id: int, db: Session):
        """Remove chunks from both SQLite and ChromaDB for a given version."""
        # Delete from SQLite
        db.query(PDFChunk).filter(PDFChunk.version_id == version_id).delete()
        db.commit()

        # Delete from ChromaDB
        if CHROMA_AVAILABLE and chroma_client:
            try:
                collection = chroma_client.get_or_create_collection(
                    name="docmind_chunks",
                    embedding_function=default_ef
                )
                # Get all chunk IDs for this version
                results = collection.get(where={"version_id": version_id})
                if results and results["ids"]:
                    collection.delete(ids=results["ids"])
            except Exception as e:
                logger.error(f"Failed to delete chunks from ChromaDB: {e}")


# Singleton
pdf_processor = PDFProcessor()
