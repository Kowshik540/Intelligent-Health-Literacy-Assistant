

import os
import re
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.rag_service import RAGService


class IngestionService:
    

    def __init__(self):
        self.rag_service = RAGService()

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

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

                    lines = text.split("\n")
                    page_text_parts = []

                    for line in lines:
                        stripped = line.strip()
                        if (
                            stripped
                            and len(stripped) < 100
                            and (stripped.isupper() or stripped.endswith(":") or re.match(r"^\d+\.?\s+\w", stripped))
                        ):
                            current_section = stripped
                        page_text_parts.append(stripped)

                    page_text = "\n".join(page_text_parts)

                    chunks = self.text_splitter.split_text(page_text)

                    for i, chunk in enumerate(chunks):
                        all_chunks.append(chunk)
                        all_metadatas.append({
                            "source": filename,
                            "page_number": str(page_num),
                            "section_header": current_section,
                            "chunk_index": len(all_chunks) - 1,
                            "total_pages": len(pdf.pages),
                        })

        except Exception as e:
            return {"chunk_count": 0, "status": "failed", "error": str(e)}

        if not all_chunks:
            return {"chunk_count": 0, "status": "failed", "error": "No text extracted from PDF"}

        chunk_count = await self.rag_service.add_documents(
            texts=all_chunks, metadatas=all_metadatas
        )

        return {"chunk_count": chunk_count, "status": "completed"}

    async def process_text_file(self, file_path: str, filename: str) -> dict:
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return await self.process_text_content(content, filename)

    async def process_text_content(self, content: str, filename: str) -> dict:
        
        chunks = self.text_splitter.split_text(content)

        if not chunks:
            return {"chunk_count": 0, "status": "failed", "error": "No text content found"}

        current_section = "Document Content"
        metadatas = []

        for i, chunk in enumerate(chunks):
            first_line = chunk.split("\n")[0].strip()
            if first_line and len(first_line) < 80 and (first_line.isupper() or first_line.endswith(":")):
                current_section = first_line

            estimated_page = (i * 1000) // 3000 + 1

            metadatas.append({
                "source": filename,
                "page_number": str(estimated_page),
                "section_header": current_section,
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

        chunk_count = await self.rag_service.add_documents(
            texts=chunks, metadatas=metadatas
        )

        return {"chunk_count": chunk_count, "status": "completed"}
