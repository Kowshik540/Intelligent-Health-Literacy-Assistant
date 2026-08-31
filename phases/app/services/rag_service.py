"""
RAG Service (Phase 2 — In Progress)
=====================================
Retrieval-Augmented Generation pipeline:
1. Embed user question using BGE model
2. Search ChromaDB for most relevant document chunks
3. Pass relevant chunks to Ollama LLM with citation instructions
4. Return answer with source document references

STATUS: Basic pipeline working. Verification layer TODO.
"""

from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOllama

from app.core.config import settings

# System prompt — constrains LLM to only use provided documents
RAG_PROMPT = """You are a health information assistant. Answer ONLY from the documents below.

RULES:
1. Use ONLY facts from the DOCUMENTS below. Do NOT use your own knowledge.
2. Keep answer under 150 words.
3. End with: [Source: filename, Page: X, Section: Y]
4. If documents don't answer the question: "I cannot provide information on this topic."

DOCUMENTS:
{context}

SOURCES:
{metadata}

QUESTION: {question}

ANSWER:"""


class RAGService:
    """Searches documents and generates cited answers using local LLM."""

    # Minimum similarity score to consider a chunk relevant
    RELEVANCE_THRESHOLD = 0.45

    def __init__(self):
        # Embedding model for vector search
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # ChromaDB vector store connection
        self.vector_store = Chroma(
            persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
            embedding_function=self.embeddings,
            collection_name="medical_documents",
        )

        # Local LLM via Ollama (no data transmitted externally)
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1,
            num_predict=200,
        )

        self.prompt = ChatPromptTemplate.from_template(RAG_PROMPT)
        self.output_parser = StrOutputParser()

    # Main method — searches documents and generates a cited answer
    async def get_response(self, question: str) -> dict:
        # Step 1: Semantic search in ChromaDB
        results = self.vector_store.similarity_search_with_relevance_scores(question, k=3)

        # Step 2: Filter by relevance threshold (reject weak matches)
        relevant = [(doc, score) for doc, score in results if score >= self.RELEVANCE_THRESHOLD]

        # If nothing relevant found, refuse to answer (prevents hallucination)
        if not relevant:
            return {
                "answer": "I cannot provide information on this topic. Please consult a healthcare professional.",
                "sources": [],
                "citations": [],
            }

        # Step 3: Build context from relevant chunks
        context_parts = []
        citations = []
        for doc, score in relevant:
            meta = doc.metadata
            context_parts.append(doc.page_content)
            citations.append({
                "source": meta.get("source", "Unknown"),
                "page_number": meta.get("page_number", "N/A"),
                "section_header": meta.get("section_header", "N/A"),
                "relevance_score": round(score, 3),
                "text_snippet": doc.page_content[:200],
            })

        context = "\n\n---\n\n".join(context_parts)
        metadata = "\n".join(f"- {c['source']}, Page {c['page_number']}" for c in citations)

        # Step 4: Generate answer using LLM (constrained to document context only)
        chain = self.prompt | self.llm | self.output_parser
        try:
            answer = await chain.ainvoke({
                "context": context, "metadata": metadata, "question": question,
            })
        except Exception as e:
            answer = f"LLM error: {str(e)}"

        return {
            "answer": answer,
            "sources": list(set(c["source"] for c in citations)),
            "citations": citations,
        }

    # TODO (Phase 2): Verification layer — retry if citations are missing from answer
    # TODO (Phase 2): LangGraph agent loop for multi-step reasoning
