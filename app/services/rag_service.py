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


# Fallback prompt used when no verified document covers the question.
# The assistant still answers from general medical knowledge, but is
# required to be safe, general, and to recommend professional care.
# It must also refuse clearly when the input is not a real health question.
GENERAL_KNOWLEDGE_PROMPT = """You are a careful health information assistant. The verified medical documents do not cover this specific question, so answer using well-established, general medical knowledge.

FIRST, decide if the user's message is actually a health or medical question.
- If the message is gibberish, random characters, or clearly NOT about health, medicine, symptoms, conditions, treatments, or wellbeing, reply with EXACTLY this and nothing else: NOT_A_HEALTH_QUESTION

Otherwise, answer using these RULES:
1. Give a helpful, accurate, general explanation that a knowledgeable health educator would give.
2. Be practical: if the user shares a reading or symptom, explain what it generally means and what is usually advised.
3. Do NOT diagnose, do NOT prescribe specific drug doses, and do NOT claim certainty about the individual.
4. Do NOT invent a symptom the user did not mention.
5. Keep the answer under 150 words in plain, clear language.
6. Always end by recommending the user confirm with a qualified healthcare professional.
7. Do NOT invent citations or reference specific documents.

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
        self.general_prompt = ChatPromptTemplate.from_template(GENERAL_KNOWLEDGE_PROMPT)
        self.output_parser = StrOutputParser()

    # Standard disclaimer appended to answers that come from general knowledge
    # rather than a verified document.
    GENERAL_DISCLAIMER = (
        "\n\nNote: This is general health information, not drawn from a specific "
        "verified document in my library. Please confirm with a qualified "
        "healthcare professional."
    )

    # Polite response when the input is not a valid health question.
    NOT_A_QUESTION_REPLY = (
        "I'm not sure I understood that as a health question. I'm a health "
        "information assistant — try asking about a symptom, condition, "
        "medicine, or general wellbeing, and I'll do my best to help."
    )

    # Generates an answer from the model's general medical knowledge when no
    # verified document covers the question. Marked clearly as general info.
    # If the input is not a real health question, returns a polite prompt to
    # rephrase instead of fabricating an answer.
    async def _general_answer(self, question: str) -> dict:
        chain = self.general_prompt | self.llm | self.output_parser
        try:
            answer = await chain.ainvoke({"question": question})
        except Exception:
            return {
                "answer": (
                    "I'm having trouble generating a response right now. "
                    "Please consult a healthcare professional for guidance."
                ),
                "sources": [],
                "citations": [],
                "is_refusal": True,
            }

        # The model flags non-health / nonsensical input so we don't hallucinate.
        if "not_a_health_question" in answer.strip().lower():
            return {
                "answer": self.NOT_A_QUESTION_REPLY,
                "sources": [],
                "citations": [],
                "not_a_question": True,
            }

        return {
            "answer": answer.strip() + self.GENERAL_DISCLAIMER,
            "sources": [],
            "citations": [],
            "from_general_knowledge": True,
        }

    # Words/phrases that indicate a greeting or small-talk rather than a medical question
    GREETING_PATTERNS = {
        "hi", "hello", "hey", "hii", "helo", "hlo", "yo", "hola",
        "good morning", "good afternoon", "good evening", "good night",
        "how are you", "how r u", "whats up", "what's up", "sup",
        "thanks", "thank you", "thankyou", "ok", "okay", "bye", "goodbye",
        "who are you", "what can you do", "help",
    }

    # Returns True when the message is a greeting/small-talk and not a real medical query
    def _is_greeting(self, question: str) -> bool:
        cleaned = question.strip().lower().strip(".!?,")
        if not cleaned:
            return True
        # Short messages that exactly match a greeting phrase
        if cleaned in self.GREETING_PATTERNS:
            return True
        # Very short single-word inputs that start like a greeting
        words = cleaned.split()
        if len(words) <= 2 and words[0] in self.GREETING_PATTERNS:
            return True
        return False

    # Main method — takes a question, retrieves relevant docs, generates a cited answer
    async def get_response(self, question: str, conversation_id: Optional[str] = None) -> dict:
        if not self.llm:
            return {
                "answer": "System error: No LLM configured.",
                "sources": [],
                "citations": [],
            }

        # Greetings and small-talk are handled directly — no document retrieval, no citations
        if self._is_greeting(question):
            return {
                "answer": (
                    "Hello. I'm a health information assistant. Ask me a health "
                    "question — for example about symptoms, conditions, or treatments — "
                    "and I'll answer using verified medical documents."
                ),
                "sources": [],
                "citations": [],
                "is_greeting": True,
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

        # Step 2: Filter to only chunks above the relevance threshold.
        # Also drop index / table-of-contents chunks, which match many
        # queries but contain no real guidance (dotted leaders, "cid:"
        # font artifacts, or the word "Index" in the section header).
        import re as _re

        def _is_index_chunk(doc) -> bool:
            text = (doc.page_content or "")
            section = (doc.metadata.get("section_header", "") or "").lower()
            # Section header explicitly says this is an index / contents page.
            if "index, volumes" in section or "table of contents" in section:
                return True
            # Dot-leaders unique to contents pages: either solid runs ("......")
            # or spaced runs (". . . . .") that pad entries before a page number.
            if "........" in text:
                return True
            if _re.search(r"(\.\s){5,}\.", text):
                return True
            # A contents entry ending in a page number after dot-leaders,
            # e.g. "Symptom management of headache . . . 202".
            if _re.search(r"\.\s*\.\s*\.\s*\d{1,4}\b", text):
                return True
            return False

        relevant_results = [
            (doc, score) for doc, score in results_with_scores
            if score >= self.RELEVANCE_THRESHOLD and not _is_index_chunk(doc)
        ]

        # If no verified chunk is relevant enough, don't just refuse — fall back
        # to general medical knowledge so the assistant is still helpful. The
        # answer is clearly labelled as general information (no citations).
        if not relevant_results:
            return await self._general_answer(question)

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

        # If the LLM decided the retrieved text does not actually answer the
        # question (e.g. it only matched an index or copyright page), fall back
        # to general medical knowledge instead of leaving the user with nothing.
        if "i cannot provide information" in answer.lower():
            return await self._general_answer(question)

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
