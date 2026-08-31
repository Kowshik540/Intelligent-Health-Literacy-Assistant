"""
Service Layer
==============
Business logic layer that orchestrates operations between the API routes,
repositories, and external services (LLM, vector store, guardrails).

Services:
- ChatService: Main orchestrator — guardrails → RAG → simplification → persistence
- RAGService: Retrieval-Augmented Generation using ChromaDB + LLM
- GuardrailsService: PII sanitization + emergency detection
- JargonSimplifier: Medical jargon → plain language rewriting
- DocumentService: Document lifecycle management
- DocumentValidationService: PDF validation pipeline
- IngestionService: PDF parsing → chunking → ChromaDB indexing
"""

from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService
from app.services.ingestion_service import IngestionService
from app.services.guardrails_service import GuardrailsService
from app.services.jargon_simplifier import JargonSimplifier
