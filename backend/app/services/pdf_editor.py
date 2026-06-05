"""
Enhanced PDF Editor for DocMind AI.
Handles page manipulation, text replacement, content generation, and diff creation.
"""
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
import os
import io
import copy
import logging
import difflib
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class PDFEditError(Exception):
    """Custom exception for PDF editing failures."""
    pass


class PDFEditor:
    """Full PDF editing engine: append, insert, replace, delete, reorder, merge, diff."""

    def create_text_page_pdf(self, title: str, paragraphs: List[str]) -> io.BytesIO:
        """Create a well-formatted single/multi-page PDF from text content."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name='DocMindTitle',
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=26,
            spaceAfter=18,
            textColor='#0f172a'
        )

        subtitle_style = ParagraphStyle(
            name='DocMindSubtitle',
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            spaceAfter=10,
            textColor='#1e293b'
        )

        body_style = ParagraphStyle(
            name='DocMindBody',
            fontName='Helvetica',
            fontSize=11,
            leading=16,
            spaceAfter=10,
            textColor='#334155',
            alignment=TA_JUSTIFY
        )

        bullet_style = ParagraphStyle(
            name='DocMindBullet',
            fontName='Helvetica',
            fontSize=11,
            leading=16,
            spaceAfter=6,
            textColor='#334155',
            leftIndent=20,
            bulletIndent=10,
            bulletText='•'
        )

        story = []

        # Title
        if title:
            story.append(Paragraph(self._escape_xml(title), title_style))
            story.append(Spacer(1, 12))

        # Process paragraphs
        for p_text in paragraphs:
            if not p_text.strip():
                story.append(Spacer(1, 8))
                continue

            # Handle bullet points
            if p_text.strip().startswith(('- ', '• ', '* ')):
                clean = p_text.strip().lstrip('-•* ').strip()
                story.append(Paragraph(self._escape_xml(clean), bullet_style))
            # Handle sub-headings (lines ending with colon or ALL CAPS short lines)
            elif (p_text.strip().endswith(':') and len(p_text.strip()) < 80) or \
                 (p_text.strip().isupper() and len(p_text.strip()) < 80):
                story.append(Spacer(1, 8))
                story.append(Paragraph(self._escape_xml(p_text.strip()), subtitle_style))
            else:
                story.append(Paragraph(self._escape_xml(p_text), body_style))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def append_page(
        self,
        input_pdf_path: str,
        output_pdf_path: str,
        title: str,
        paragraphs: List[str]
    ) -> bool:
        """Append new pages to the end of a PDF."""
        try:
            new_page_io = self.create_text_page_pdf(title, paragraphs)
            new_page_doc = fitz.open("pdf", new_page_io.read())

            original_doc = fitz.open(input_pdf_path)
            original_doc.insert_pdf(new_page_doc)
            original_doc.save(output_pdf_path)

            original_doc.close()
            new_page_doc.close()
            return True
        except Exception as e:
            logger.error(f"Failed to append page: {e}")
            raise PDFEditError(f"Failed to append page: {str(e)}")

    def insert_page_at(
        self,
        input_pdf_path: str,
        output_pdf_path: str,
        page_index: int,
        title: str,
        paragraphs: List[str]
    ) -> bool:
        """Insert new pages at a specific position (0-indexed)."""
        try:
            original_doc = fitz.open(input_pdf_path)
            
            if page_index < 0 or page_index > len(original_doc):
                msg = f"Insertion index {page_index + 1} is out of range (document has {len(original_doc)} pages)."
                original_doc.close()
                raise PDFEditError(msg)

            new_page_io = self.create_text_page_pdf(title, paragraphs)
            new_page_doc = fitz.open("pdf", new_page_io.read())
            
            # Build new document: pages before insert point + new pages + pages after
            result_doc = fitz.open()
            
            # Pages before insert point
            if page_index > 0:
                result_doc.insert_pdf(original_doc, from_page=0, to_page=page_index - 1)
            
            # New pages
            result_doc.insert_pdf(new_page_doc)
            
            # Pages after insert point
            if page_index < len(original_doc):
                result_doc.insert_pdf(original_doc, from_page=page_index, to_page=len(original_doc) - 1)

            result_doc.save(output_pdf_path)
            result_doc.close()
            original_doc.close()
            new_page_doc.close()
            return True
        except PDFEditError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to insert page at {page_index}: {e}")
            raise PDFEditError(f"Failed to insert page: {str(e)}")

    def replace_text(
        self,
        input_pdf_path: str,
        output_pdf_path: str,
        page_number: int,
        target_text: str,
        replacement_text: str
    ) -> bool:
        """Find and replace text on a specific page (page_number is 1-indexed)."""
        try:
            doc = fitz.open(input_pdf_path)
            page_idx = page_number - 1

            if page_idx < 0 or page_idx >= len(doc):
                msg = f"Page {page_number} is out of range (document has {len(doc)} pages)."
                logger.error(msg)
                doc.close()
                raise PDFEditError(msg)

            page = doc[page_idx]
            rects = page.search_for(target_text)

            if not rects:
                msg = f"Target text '{target_text}' not found on page {page_number}."
                logger.warning(msg)
                doc.close()
                raise PDFEditError(msg)

            # Redact old text
            for rect in rects:
                page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

            # Insert replacement text
            first_rect = rects[0]
            # Expand rect to accommodate longer replacement text
            text_rect = fitz.Rect(
                first_rect.x0,
                first_rect.y0,
                min(first_rect.x1 + 200, page.rect.width - 54),
                min(first_rect.y1 + 100, page.rect.height - 54)
            )

            page.insert_textbox(
                text_rect,
                replacement_text,
                fontsize=10,
                fontname="helv",
                color=(0.1, 0.1, 0.1),
                align=fitz.TEXT_ALIGN_LEFT
            )

            doc.save(output_pdf_path)
            doc.close()
            return True
        except PDFEditError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to replace text: {e}")
            raise PDFEditError(f"Failed to replace text: {str(e)}")

    def replace_page_content(
        self,
        input_pdf_path: str,
        output_pdf_path: str,
        page_number: int,
        new_title: str,
        new_paragraphs: List[str]
    ) -> bool:
        """Replace entire page content by deleting the page and inserting a new one."""
        try:
            doc = fitz.open(input_pdf_path)
            page_idx = page_number - 1

            if page_idx < 0 or page_idx >= len(doc):
                msg = f"Page {page_number} is out of range (document has {len(doc)} pages)."
                doc.close()
                raise PDFEditError(msg)

            # Create new page content
            new_page_io = self.create_text_page_pdf(new_title, new_paragraphs)
            new_page_doc = fitz.open("pdf", new_page_io.read())

            # Build result: before + new + after
            result_doc = fitz.open()

            if page_idx > 0:
                result_doc.insert_pdf(doc, from_page=0, to_page=page_idx - 1)
            
            result_doc.insert_pdf(new_page_doc)

            if page_idx + 1 < len(doc):
                result_doc.insert_pdf(doc, from_page=page_idx + 1, to_page=len(doc) - 1)

            result_doc.save(output_pdf_path)
            result_doc.close()
            doc.close()
            new_page_doc.close()
            return True
        except PDFEditError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to replace page content: {e}")
            raise PDFEditError(f"Failed to replace page content: {str(e)}")

    def delete_pages(
        self,
        input_pdf_path: str,
        output_pdf_path: str,
        page_numbers: List[int]
    ) -> bool:
        """Delete specified pages (1-indexed) from a PDF."""
        try:
            doc = fitz.open(input_pdf_path)
            
            # Check if any requested page number is out of bounds
            invalid_pages = [p for p in page_numbers if p <= 0 or p > len(doc)]
            if invalid_pages:
                msg = f"Cannot delete pages {invalid_pages} because they are out of range (document has {len(doc)} pages)."
                logger.error(msg)
                doc.close()
                raise PDFEditError(msg)

            pages_to_delete = sorted([p - 1 for p in page_numbers], reverse=True)

            if len(pages_to_delete) >= len(doc):
                msg = "Cannot delete all pages from the PDF. At least one page must remain."
                logger.error(msg)
                doc.close()
                raise PDFEditError(msg)

            for page_idx in pages_to_delete:
                doc.delete_page(page_idx)

            doc.save(output_pdf_path)
            doc.close()
            return True
        except PDFEditError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to delete pages: {e}")
            raise PDFEditError(f"Failed to delete pages: {str(e)}")

    def get_page_text(self, file_path: str, page_number: int) -> str:
        """Get text content of a specific page (1-indexed)."""
        try:
            doc = fitz.open(file_path)
            page_idx = page_number - 1
            if page_idx < 0 or page_idx >= len(doc):
                doc.close()
                return ""
            text = doc[page_idx].get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"Failed to get page text: {e}")
            return ""

    def get_page_count(self, file_path: str) -> int:
        """Get the total number of pages in a PDF."""
        try:
            doc = fitz.open(file_path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0

    def generate_text_diff(
        self,
        old_text: str,
        new_text: str
    ) -> List[Dict[str, Any]]:
        """Generate a structured diff between two text blocks."""
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        differ = difflib.unified_diff(old_lines, new_lines, lineterm='')
        
        diff_result = []
        for line in differ:
            if line.startswith('+++') or line.startswith('---'):
                continue
            elif line.startswith('@@'):
                diff_result.append({"type": "header", "content": line})
            elif line.startswith('+'):
                diff_result.append({"type": "added", "content": line[1:]})
            elif line.startswith('-'):
                diff_result.append({"type": "removed", "content": line[1:]})
            else:
                diff_result.append({"type": "unchanged", "content": line})

        return diff_result

    def copy_pdf(self, source_path: str, dest_path: str) -> bool:
        """Copy a PDF file to a new location."""
        try:
            import shutil
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(source_path, dest_path)
            return True
        except Exception as e:
            logger.error(f"Failed to copy PDF: {e}")
            return False

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape special XML characters for ReportLab."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))


# Singleton
pdf_editor = PDFEditor()
