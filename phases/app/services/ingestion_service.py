"""
Document Ingestion Service (Phase 1)
======================================
Handles the complete PDF ingestion pipeline:
1. Extract text from PDF pages using pdfplumber
2. Split into semantic chunks (~1000 chars, 200 overlap)
3. Tag each chunk with metadata (source filename, page number, section header)
4. Embed using BGE model and store in ChromaDB

This makes medical documents searchable by meaning rather than keywords.
"""

import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.core.config import settings


class IngestionService:
    """Processes medical PDFs and stores their vector embeddings in ChromaDB."""

    def __init__(self):
        # BGE embedding model — converts text to 384-dimensional vectors
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # ChromaDB vector store — persists embeddings to disk
        self.vector_store = Chroma(
            persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
            embedding_function=self.embeddings,
            collection_name="medical_documents",
        )

        # Section-aware text splitter (1000 chars with 200 overlap)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    # Extracts text from a PDF, chunks it, and stores embeddings in ChromaDB
    async def process_pdf(self, file_path: str, filename: str) -> dict:
        try:
            import pdfplumber
        except ImportError:
            return {"chunk_count": 0, "status": "failed", "error": "pdfplumber not installed"}

        all_chunks = []
        all_metadatas = []
        current_section = "Introduction"

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if not text:
                        continue

                    # Detect section headers from the text
                    lines = text.split("\n")
                    page_text_parts = []

                    for line in lines:
                        stripped = line.strip()
                        if (stripped and len(stripped) < 100
                                and (stripped.isupper() or stripped.endswith(":")
                                     or re.match(r"^\d+\.?\s+\w", stripped))):
                            current_section = stripped
                        page_text_parts.append(stripped)

                    page_text = "\n".join(page_text_parts)
                    chunks = self.text_splitter.split_text(page_text)

                    # Tag each chunk with source metadata for citations
                    for chunk in chunks:
                        all_chunks.append(chunk)
                        all_metadatas.append({
                            "source": filename,
                            "page_number": str(page_num),
                            "section_header": current_section,
                            "chunk_index": len(all_chunks) - 1,
                        })

        except Exception as e:
            return {"chunk_count": 0, "status": "failed", "error": str(e)}

        if not all_chunks:
            return {"chunk_count": 0, "status": "failed", "error": "No text extracted from PDF"}

        # Store all chunks in ChromaDB
        self.vector_store.add_texts(texts=all_chunks, metadatas=all_metadatas)
        return {"chunk_count": len(all_chunks), "status": "completed"}

    # Processes plain text files (guidelines in .txt format)
    async def process_text_file(self, file_path: str, filename: str) -> dict:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = self.text_splitter.split_text(content)
        if not chunks:
            return {"chunk_count": 0, "status": "failed", "error": "No content"}

        metadatas = [{
            "source": filename,
            "page_number": str((i * 1000) // 3000 + 1),
            "section_header": "Document Content",
            "chunk_index": i,
        } for i, _ in enumerate(chunks)]

        self.vector_store.add_texts(texts=chunks, metadatas=metadatas)
        return {"chunk_count": len(chunks), "status": "completed"}
