"""
RAG Service — Retrieval-Augmented Generation Pipeline.
This is the core AI engine: searches ChromaDB for relevant medical documents,
then passes them to the LLM to generate a cited, factual answer.

Flow: User Question → Embedding → ChromaDB Search → LLM Generation → Cited Answer
"""

from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.core.config import settings


# System prompt that constrains the LLM to answer ONLY from provided documents
CLINICAL_RAG_PROMPT = """You are a health information assistant. You can ONLY use the exact text in the DOCUMENTS section below. Do NOT add any information from your own knowledge.

STRICT RULES:
1. ONLY state facts that appear word-for-word or clearly stated in the DOCUMENTS below.
2. If the documents only contain an index, table of contents, or page references — say "I cannot provide information on this topic."
3. Do NOT give general medical advice that isn't directly from the documents.
4. Keep your answer under 150 words.
5. End with: [Source: filename, Page: X, Section: Y]
6. If the documents don't contain a real answer, say: "I cannot provide information on this topic based on my verified medical documents. Please consult a healthcare professional."

DOCUMENTS:
{context}

SOURCES:
{metadata}

QUESTION: {question}

ANSWER:"""


class RAGService:
    """Retrieval-Augmented Generation — searches documents and generates cited answers."""

    # Minimum relevance score for a document chunk to be used in answer generation
    RELEVANCE_THRESHOLD = 0.45

    # Initializes the embedding model, vector store, and LLM connection
    def __init__(self):
        # BGE embedding model for converting text to vectors
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # ChromaDB vector store — persists embeddings locally
        self.vector_store = Chroma(
            persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
            embedding_function=self.embeddings,
            collection_name="medical_documents",
        )

        # LLM configuration — Ollama (local) or OpenAI (cloud)
        if settings.USE_OLLAMA:
            from langchain_community.chat_models import ChatOllama
            self.llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.1,
                num_predict=200,
            )
        elif settings.OPENAI_API_KEY:
            self.llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=0.1,
                api_key=settings.OPENAI_API_KEY,
            )
        else:
            self.llm = None

        self.prompt = ChatPromptTemplate.from_template(CLINICAL_RAG_PROMPT)
        self.output_parser = StrOutputParser()

    # Main method — takes a question, retrieves relevant docs, generates a cited answer
    async def get_response(self, question: str, conversation_id: Optional[str] = None) -> dict:
        if not self.llm:
            return {
                "answer": "System error: No LLM configured.",
                "sources": [],
                "citations": [],
            }

        # Step 1: Semantic search in ChromaDB for the most relevant document chunks
        results_with_scores = self.vector_store.similarity_search_with_relevance_scores(
            query=question,
            k=3,
        )

        # Build citations from ALL results (shown in sidebar regardless of threshold)
        all_citations = []
        for doc, score in results_with_scores:
            meta = doc.metadata
            source_name = meta.get("source", "Unknown Document")
            page_num = meta.get("page_number", "N/A")
            section = meta.get("section_header", "N/A")
            all_citations.append({
                "source": source_name,
                "page_number": page_num,
                "section_header": section,
                "relevance_score": round(score, 3),
                "text_snippet": doc.page_content[:200],
            })

        # Step 2: Filter to only chunks above the relevance threshold
        relevant_results = [
            (doc, score) for doc, score in results_with_scores
            if score >= self.RELEVANCE_THRESHOLD
        ]

        # If no chunks are relevant enough, refuse to answer rather than hallucinate
        if not relevant_results:
            return {
                "answer": (
                    "I cannot provide information on this topic. The medical documents "
                    "in my database do not contain relevant information about your question. "
                    "Please consult a healthcare professional for guidance."
                ),
                "sources": [c["source"] for c in all_citations[:2]],
                "citations": all_citations,
            }

        # Step 3: Build context from relevant chunks for the LLM
        context_parts = []
        metadata_parts = []
        citations = []

        for doc, score in relevant_results:
            meta = doc.metadata
            source_name = meta.get("source", "Unknown Document")
            page_num = meta.get("page_number", "N/A")
            section = meta.get("section_header", "N/A")

            context_parts.append(doc.page_content)
            metadata_parts.append(
                f"- Document: {source_name}, Page: {page_num}, Section: {section}, Relevance: {score:.2f}"
            )
            citations.append({
                "source": source_name,
                "page_number": page_num,
                "section_header": section,
                "relevance_score": round(score, 3),
                "text_snippet": doc.page_content[:200],
            })

        context = "\n\n---\n\n".join(context_parts)
        metadata = "\n".join(metadata_parts)

        # Step 4: Pass context + question to the LLM for answer generation
        chain = self.prompt | self.llm | self.output_parser

        try:
            answer = await chain.ainvoke({
                "context": context,
                "metadata": metadata,
                "question": question,
            })
        except Exception as e:
            answer = (
                "I found relevant medical documents but could not generate a response. "
                f"Please ensure the LLM service is running. Error: {str(e)}"
            )

        sources = list(set([c["source"] for c in citations]))

        return {
            "answer": answer,
            "sources": sources,
            "citations": citations,
        }

    # Adds new document chunks to ChromaDB (used by the ingestion pipeline)
    async def add_documents(self, texts: list[str], metadatas: list[dict]) -> int:
        if not texts:
            return 0
        self.vector_store.add_texts(texts=texts, metadatas=metadatas)
        return len(texts)
