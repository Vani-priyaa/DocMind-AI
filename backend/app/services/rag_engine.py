"""
RAG Engine for DocMind AI.
Central orchestrator for retrieval-augmented generation, summarization, and edit commands.
"""
import logging
import os
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.all_models import (
    PDFDocument, PDFVersion, PDFChunk, Message, PDFEditPreview
)
from app.services.gemini_client import gemini_client
from app.services.pdf_processor import pdf_processor
from app.services.pdf_editor import pdf_editor, PDFEditError
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Retrieval-Augmented Generation engine for DocMind AI.
    Handles Q&A, summarization, editing, and suggestions.
    """

    async def answer_question(
        self,
        query: str,
        document_id: int,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline:
        1. Get active version
        2. Retrieve relevant chunks
        3. Build context with citations
        4. Generate answer via Gemini
        5. Extract citations
        6. Return answer + sources
        """
        # Get latest version
        version = self._get_latest_version(document_id, db)
        if not version:
            return {"answer": "No document version found.", "sources": [], "follow_ups": []}

        # Get conversation history
        history = self._get_conversation_history(document_id, db)

        # Retrieve relevant chunks
        chunks = pdf_processor.search_chunks(version.id, query, limit=6, db=db)

        if not chunks:
            return {
                "answer": "I couldn't find relevant content in the document for this question.",
                "sources": [],
                "follow_ups": ["Can you summarize the document?", "What topics does this document cover?"]
            }

        # Generate answer with Gemini
        answer = await gemini_client.generate_with_context(
            query=query,
            context_chunks=chunks,
            conversation_history=history,
        )

        # Extract page citations from the answer
        sources = self._extract_citations(answer, chunks)

        # Generate follow-up questions
        follow_ups = await self._generate_follow_ups(query, answer, chunks)

        return {
            "answer": answer,
            "sources": sources,
            "follow_ups": follow_ups,
        }

    async def summarize_document(
        self,
        document_id: int,
        db: Session,
        mode: str = "executive",
        pages: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Summarize document content.
        Modes: executive, bullet, technical
        Can summarize specific pages or the entire document.
        """
        version = self._get_latest_version(document_id, db)
        if not version:
            return {"summary": "No document found.", "sources": []}

        # Get chunks for specified pages or all
        if pages:
            chunks = db.query(PDFChunk).filter(
                PDFChunk.version_id == version.id,
                PDFChunk.page_number.in_(pages)
            ).all()
        else:
            chunks = db.query(PDFChunk).filter(
                PDFChunk.version_id == version.id
            ).all()

        if not chunks:
            return {"summary": "No content found to summarize.", "sources": []}

        # Build content for summarization
        content = ""
        source_pages = set()
        for chunk in chunks[:12]:  # Limit to avoid token overflow / API rate limits
            content += f"\n[Page {chunk.page_number}]: {chunk.content[:800]}"
            source_pages.add(chunk.page_number)

        mode_instructions = {
            "executive": "Provide a 2-3 paragraph executive summary suitable for senior leadership.",
            "bullet": "Provide a bullet-point summary with key topics and findings. Use - for each point.",
            "technical": "Provide a detailed technical summary covering specifications, architectures, and technical details.",
        }

        instruction = mode_instructions.get(mode, mode_instructions["executive"])

        prompt = f"""{instruction}

DOCUMENT CONTENT:
{content}

RULES:
1. Cite page numbers using [Page X] format.
2. Be accurate and only reference information from the provided content.
3. Structure the summary clearly."""

        summary = await gemini_client.generate(
            prompt=prompt,
            system_instruction="You are DocMind AI, a document summarization expert. Always cite page numbers.",
            temperature=0.3,
        )

        sources = [{"page_number": p} for p in sorted(source_pages)]

        return {
            "summary": summary,
            "mode": mode,
            "sources": sources,
            "page_count": len(source_pages),
        }

    async def process_edit_command(
        self,
        command: str,
        document_id: int,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Process a natural language edit command.
        Returns a preview of the proposed changes.
        """
        version = self._get_latest_version(document_id, db)
        if not version:
            return {"error": "No document version found."}

        # Retrieve relevant content for the edit
        chunks = pdf_processor.search_chunks(version.id, command, limit=8, db=db)

        # Generate edit plan using Gemini
        edit_plan = await gemini_client.generate_edit_plan(
            command=command,
            relevant_content=chunks,
        )

        if not edit_plan or not edit_plan.get("action"):
            return {
                "error": "I couldn't understand the edit command. Please try rephrasing.",
                "suggestion": "Try commands like: 'Add a conclusion page', 'Rewrite section 3 in simpler language', 'Replace the introduction with a summary'"
            }

        # Store the edit preview
        preview = PDFEditPreview(
            document_id=document_id,
            version_id=version.id,
            command=command,
            edit_plan=edit_plan,
            status="pending"
        )
        db.add(preview)
        db.commit()
        db.refresh(preview)

        # Generate diff preview if replacing text
        diff = []
        if edit_plan.get("action") == "replace_text" and edit_plan.get("original_text"):
            diff = pdf_editor.generate_text_diff(
                edit_plan.get("original_text", ""),
                edit_plan.get("new_content", "")
            )

        return {
            "preview_id": preview.id,
            "action": edit_plan.get("action"),
            "description": edit_plan.get("description", ""),
            "preview_summary": edit_plan.get("preview_summary", ""),
            "target_pages": edit_plan.get("target_pages", []),
            "new_content_preview": (edit_plan.get("new_content", ""))[:500],
            "diff": diff,
            "status": "pending_confirmation"
        }

    async def apply_edit(
        self,
        preview_id: int,
        document_id: int,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Apply a confirmed edit to create a new version of the document.
        """
        # Get the preview
        preview = db.query(PDFEditPreview).filter(
            PDFEditPreview.id == preview_id,
            PDFEditPreview.document_id == document_id,
            PDFEditPreview.status == "pending"
        ).first()

        if not preview:
            return {"error": "Edit preview not found or already applied."}

        edit_plan = preview.edit_plan
        current_version = db.query(PDFVersion).filter(
            PDFVersion.id == preview.version_id
        ).first()

        if not current_version or not os.path.exists(current_version.file_path):
            return {"error": "Source PDF file not found."}

        # Create new version number
        doc = db.query(PDFDocument).filter(PDFDocument.id == document_id).first()
        new_version_num = current_version.version_number + 1
        
        # Create output path
        doc_dir = os.path.dirname(current_version.file_path)
        new_file_path = os.path.join(doc_dir, f"v{new_version_num}.pdf")

        # Apply the edit based on action type
        action = edit_plan.get("action", "")
        success = False

        try:
            if action == "append_page":
                title = edit_plan.get("title", "New Section")
                content = edit_plan.get("new_content", "")
                paragraphs = [p for p in content.split("\n") if p.strip()]
                success = pdf_editor.append_page(
                    current_version.file_path, new_file_path, title, paragraphs
                )

            elif action == "insert_page":
                title = edit_plan.get("title", "New Section")
                content = edit_plan.get("new_content", "")
                paragraphs = [p for p in content.split("\n") if p.strip()]
                target_pages = edit_plan.get("target_pages", [1])
                page_idx = (target_pages[0] - 1) if target_pages else 0
                success = pdf_editor.insert_page_at(
                    current_version.file_path, new_file_path, page_idx, title, paragraphs
                )

            elif action == "replace_text":
                target_pages = edit_plan.get("target_pages", [1])
                page_num = target_pages[0] if target_pages else 1
                success = pdf_editor.replace_text(
                    current_version.file_path, new_file_path,
                    page_num,
                    edit_plan.get("original_text", ""),
                    edit_plan.get("new_content", "")
                )

            elif action == "rewrite_section":
                target_pages = edit_plan.get("target_pages", [1])
                page_num = target_pages[0] if target_pages else 1
                title = edit_plan.get("title", "")
                content = edit_plan.get("new_content", "")
                paragraphs = [p for p in content.split("\n") if p.strip()]
                success = pdf_editor.replace_page_content(
                    current_version.file_path, new_file_path, page_num, title, paragraphs
                )

            elif action == "delete_page":
                target_pages = edit_plan.get("target_pages", [])
                if target_pages:
                    success = pdf_editor.delete_pages(
                        current_version.file_path, new_file_path, target_pages
                    )

            else:
                # Default: append as new content
                title = edit_plan.get("title", "Generated Content")
                content = edit_plan.get("new_content", "")
                paragraphs = [p for p in content.split("\n") if p.strip()]
                success = pdf_editor.append_page(
                    current_version.file_path, new_file_path, title, paragraphs
                )
        except PDFEditError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to edit PDF: {str(e)}"}

        if not success:
            return {"error": "Failed to apply the edit to the PDF."}

        # Create new version record
        new_version = PDFVersion(
            document_id=document_id,
            version_number=new_version_num,
            file_path=new_file_path,
            change_description=preview.command,
        )
        db.add(new_version)

        # Update preview status
        preview.status = "applied"
        
        db.commit()
        db.refresh(new_version)

        # Re-index the new version
        try:
            extracted = pdf_processor.extract_text_and_metadata(new_file_path)
            chunks = pdf_processor.chunk_document(extracted["pages"])
            pdf_processor.index_chunks(db, new_version.id, chunks)
            
            # Update page count
            doc.page_count = extracted["page_count"]
            db.commit()
        except Exception as e:
            logger.error(f"Failed to re-index after edit: {e}")

        return {
            "success": True,
            "version_id": new_version.id,
            "version_number": new_version_num,
            "description": edit_plan.get("description", "Edit applied"),
            "page_count": pdf_editor.get_page_count(new_file_path),
        }

    async def get_autocomplete_suggestions(
        self,
        partial_query: str,
        document_id: int,
        db: Session,
    ) -> List[str]:
        """
        Generate real-time autocomplete suggestions grounded in document content.
        """
        if len(partial_query) < 2:
            return []

        version = self._get_latest_version(document_id, db)
        if not version:
            return []

        # Check if we have pre-generated suggestions
        suggestions_data = version.suggestions
        stored_questions = []
        topics = []
        headings = []

        if suggestions_data:
            if isinstance(suggestions_data, str):
                try:
                    suggestions_data = json.loads(suggestions_data)
                except json.JSONDecodeError:
                    suggestions_data = {}
            
            stored_questions = suggestions_data.get("suggested_questions", [])
            topics = suggestions_data.get("topics", [])
            headings = suggestions_data.get("headings", [])

        # First: filter stored questions by prefix match
        prefix_lower = partial_query.lower()
        matched = [q for q in stored_questions if prefix_lower in q.lower()]

        # Supplement matches from headings and topics locally (instant, zero cost)
        for h in headings:
            if prefix_lower in h.lower() and len(matched) < 5:
                q = f"Tell me about {h}"
                if q not in matched:
                    matched.append(q)

        for t in topics:
            if prefix_lower in t.lower() and len(matched) < 5:
                q = f"What is the detail on {t}?"
                if q not in matched:
                    matched.append(q)

        if len(matched) >= 3:
            return matched[:5]

        # Check in-memory cache
        if not hasattr(self, "_suggestion_cache"):
            self._suggestion_cache = {}
        if not hasattr(self, "_last_suggestion_time"):
            self._last_suggestion_time = {}

        query_key = (document_id, prefix_lower)
        if query_key in self._suggestion_cache:
            return self._suggestion_cache[query_key]

        # Cooldown: limit LLM suggestion queries to once every 3 seconds per document
        import time
        now = time.time()
        last_time = self._last_suggestion_time.get(document_id, 0)
        if now - last_time < 3.0:
            logger.info("Autocomplete LLM request throttled due to cooldown.")
            return matched[:5]

        self._last_suggestion_time[document_id] = now

        # If not enough matches, use Gemini for real-time generation
        try:
            ai_suggestions = await gemini_client.generate_suggestions(
                partial_query=partial_query,
                document_topics=topics,
                document_headings=headings,
            )
            # Combine and deduplicate
            all_suggestions = matched + [s for s in ai_suggestions if s not in matched]
            res = all_suggestions[:5]
            self._suggestion_cache[query_key] = res
            return res
        except Exception as e:
            logger.error(f"Autocomplete generation failed: {e}")
            return matched[:5]

    def _get_latest_version(self, document_id: int, db: Session) -> Optional[PDFVersion]:
        """Get the latest version of a document."""
        return db.query(PDFVersion).filter(
            PDFVersion.document_id == document_id
        ).order_by(PDFVersion.version_number.desc()).first()

    def _get_conversation_history(
        self,
        document_id: int,
        db: Session,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """Get recent conversation history for a document."""
        messages = db.query(Message).filter(
            Message.session_id == document_id  # Using document_id as session context
        ).order_by(Message.created_at.desc()).limit(limit).all()

        history = [{"role": m.role, "content": m.content} for m in reversed(messages)]
        return history

    def _extract_citations(
        self,
        answer: str,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract page citations from the answer and map to source chunks."""
        import re
        
        # Find all [Page X] references
        page_refs = re.findall(r'\[Page\s+(\d+)\]', answer)
        cited_pages = set(int(p) for p in page_refs)

        sources = []
        seen_pages = set()
        
        for chunk in chunks:
            page_num = chunk.get("page_number")
            if page_num in cited_pages and page_num not in seen_pages:
                sources.append({
                    "page_number": page_num,
                    "heading": chunk.get("heading", ""),
                    "snippet": chunk.get("content", "")[:200],
                })
                seen_pages.add(page_num)

        # Also include top chunks that weren't explicitly cited
        for chunk in chunks:
            page_num = chunk.get("page_number")
            if page_num not in seen_pages:
                sources.append({
                    "page_number": page_num,
                    "heading": chunk.get("heading", ""),
                    "snippet": chunk.get("content", "")[:200],
                })
                seen_pages.add(page_num)
            if len(sources) >= 5:
                break

        return sources

    async def _generate_follow_ups(
        self,
        query: str,
        answer: str,
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate follow-up question suggestions."""
        try:
            prompt = f"""Based on this Q&A exchange about a document, suggest 3 natural follow-up questions.

Question: {query}
Answer: {answer[:500]}

Return ONLY a JSON array of 3 question strings. Example: ["What are the details of X?", "How does Y relate to Z?", "Can you summarize W?"]"""

            raw = await gemini_client.generate(prompt=prompt, temperature=0.4, max_tokens=300)
            
            import re
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                follow_ups = json.loads(match.group(0))
                if isinstance(follow_ups, list):
                    return [q for q in follow_ups if isinstance(q, str)][:3]
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")

        return []


# Singleton
rag_engine = RAGEngine()
