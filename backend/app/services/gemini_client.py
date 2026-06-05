"""
Google Gemini AI Client for DocMind AI.
Provides text generation, embeddings, and streaming responses.
"""
import logging
import json
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini
_genai = None
_model = None

def _get_genai():
    global _genai
    if _genai is None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            _genai = genai
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    return _genai

def _get_model():
    global _model
    if _model is None:
        genai = _get_genai()
        _model = genai.GenerativeModel(settings.GEMINI_MODEL)
    return _model


class GeminiClient:
    """Wrapper around Google Gemini API with retry logic and structured output."""

    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 1.0

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text response from Gemini, falling back to NVIDIA NIM or OpenAI on failure."""
        use_gemini = True
        
        # If the API key is not configured, or we know it's suspended
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY in ["", "YOUR_GEMINI_API_KEY_HERE"]:
            use_gemini = False
            
        if use_gemini:
            for attempt in range(self.max_retries):
                try:
                    genai = _get_genai()
                    
                    # Create model with system instruction if provided
                    if system_instruction:
                        model = genai.GenerativeModel(
                            settings.GEMINI_MODEL,
                            system_instruction=system_instruction
                        )
                    else:
                        model = _get_model()

                    generation_config = genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    )

                    response = await asyncio.to_thread(
                        model.generate_content,
                        prompt,
                        generation_config=generation_config,
                    )
                    
                    if response and response.text:
                        return response.text
                    
                    logger.warning(f"Empty response from Gemini on attempt {attempt + 1}")
                    
                except Exception as e:
                    logger.warning(f"Gemini generation failed (attempt {attempt + 1}): {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    else:
                        logger.warning("Gemini API calls failed completely. Moving to fallback providers...")

        # Fallback 1: NVIDIA NIM
        if settings.NVIDIA_API_KEY and settings.NVIDIA_API_KEY != "YOUR_NVIDIA_API_KEY_HERE":
            try:
                logger.info("Attempting fallback generation using NVIDIA NIM...")
                from openai import AsyncOpenAI
                client = AsyncOpenAI(
                    api_key=settings.NVIDIA_API_KEY,
                    base_url="https://integrate.api.nvidia.com/v1"
                )
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                response = await client.chat.completions.create(
                    model="meta/llama-3.1-70b-instruct",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 2048)
                )
                if response and response.choices:
                    val = response.choices[0].message.content
                    if val:
                        logger.info("NVIDIA NIM fallback generation succeeded!")
                        return val
            except Exception as nv_err:
                logger.error(f"NVIDIA NIM fallback failed: {nv_err}")

        # Fallback 2: OpenAI
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "YOUR_OPENAI_API_KEY_HERE":
            try:
                logger.info("Attempting fallback generation using OpenAI...")
                from openai import AsyncOpenAI
                client = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY
                )
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if response and response.choices:
                    val = response.choices[0].message.content
                    if val:
                        logger.info("OpenAI fallback generation succeeded!")
                        return val
            except Exception as oa_err:
                logger.error(f"OpenAI fallback failed: {oa_err}")

        raise Exception("All text generation providers (Gemini, NVIDIA, OpenAI) failed or were not configured.")

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Generate and parse JSON response from Gemini."""
        raw = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self._parse_json(raw)

    async def generate_with_context(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Generate response using RAG context and conversation history."""
        # Build context block
        context_text = ""
        for i, chunk in enumerate(context_chunks):
            page = chunk.get("page_number", "?")
            heading = chunk.get("heading", "")
            content = chunk.get("content", "")
            context_text += f"\n\n--- SOURCE {i+1} (Page {page}{f', Section: {heading}' if heading else ''}) ---\n{content}"

        # Build conversation history
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")[:500]
                history_text += f"\n{role.upper()}: {content}"

        full_prompt = f"""RETRIEVED DOCUMENT CONTEXT:
{context_text}

{"CONVERSATION HISTORY:" + history_text if history_text else ""}

USER QUESTION: {query}

INSTRUCTIONS:
1. Answer the question using ONLY the provided document context.
2. If the answer is not in the context, say "I couldn't find information about that in the document."
3. Always cite your sources using [Page X] format after relevant statements.
4. Be precise and professional.
5. If the user asks for a summary, provide a structured summary.
"""

        default_system = """You are DocMind AI, an intelligent PDF document assistant. 
You help users understand, analyze, and modify PDF documents.
You always cite page numbers when referencing document content.
You are professional, precise, and helpful."""

        return await self.generate(
            prompt=full_prompt,
            system_instruction=system_instruction or default_system,
            temperature=0.3,
            max_tokens=4096,
        )

    async def generate_suggestions(
        self,
        partial_query: str,
        document_topics: List[str],
        document_headings: List[str],
    ) -> List[str]:
        """Generate autocomplete suggestions grounded in document content."""
        prompt = f"""Given a user is typing a question about a document, generate 5 autocomplete suggestions.

The user has typed: "{partial_query}"

Document topics: {', '.join(document_topics[:20])}
Document headings: {', '.join(document_headings[:20])}

Return ONLY a JSON array of 5 complete question strings that start with or are related to what the user typed.
The suggestions must be grounded in the document's actual content.

Example format: ["What are the system requirements?", "What is the deployment process?"]"""

        try:
            raw = await self.generate(prompt=prompt, temperature=0.3, max_tokens=500)
            # Parse JSON array
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                suggestions = json.loads(match.group(0))
                if isinstance(suggestions, list):
                    return [s for s in suggestions if isinstance(s, str)][:5]
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")

        return []

    async def generate_edit_plan(
        self,
        command: str,
        relevant_content: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Parse a natural language edit command into an actionable edit plan."""
        context = ""
        for chunk in relevant_content:
            page = chunk.get("page_number", "?")
            content = chunk.get("content", "")[:500]
            context += f"\n[Page {page}]: {content}"

        prompt = f"""Analyze this document editing command and create an edit plan.

COMMAND: "{command}"

RELEVANT DOCUMENT CONTENT:
{context}

Return a JSON object with this structure:
{{
    "action": "append_page" | "insert_page" | "replace_text" | "rewrite_section" | "delete_page",
    "target_pages": [1, 2],
    "title": "Title for new content if applicable",
    "original_text": "Text to find/replace if applicable",
    "new_content": "The generated/modified content",
    "description": "Human-readable description of the change",
    "preview_summary": "Brief summary of what will change"
}}

Generate the actual content for new_content based on the command and document context."""

        return await self.generate_json(
            prompt=prompt,
            temperature=0.3,
            max_tokens=4096,
        )

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Resilient JSON parser that handles markdown code blocks and malformed JSON."""
        if not text:
            return {}

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if code_block:
            try:
                return json.loads(code_block.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding the largest JSON object
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse JSON from response: {text[:200]}")
        return {}


# Singleton instance
gemini_client = GeminiClient()
