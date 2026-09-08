"""
Retrieval-augmented generation: embed the question, search ChromaDB, and have
the LLM answer from the retrieved documents with citations.
"""

import asyncio
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.services.llm_factory import build_chat_llm, build_embeddings, build_chroma


# System prompt that constrains the LLM to answer ONLY from provided documents
CLINICAL_RAG_PROMPT = """You are a board-certified Clinical Decision Support and Patient Health assistant. Deliver safe, accurate, empathetic, and SCANNABLE guidance. Ground your answer in the DOCUMENTS section below.

THE FIRST-TWO-SENTENCES LAW:
Open with the bottom-line assessment or the primary safety action. No greetings, no filler, no preamble.

STRICT RULES:
1. VITALS OVERRIDE: The patient's vital signs have already been classified for you (see FACTS). Never compute, alter, or contradict those classifications. If a value is marked "Normal", tell the patient it is normal and healthy. Never evaluate numeric thresholds yourself and never re-label a value. State the classification as a plain clinical fact (e.g., "Your blood pressure of 110/60 is normal") — do NOT say it "was provided", "was classified by a rule engine", or "in the documents".
2. TRIAGE FIRST: If the triage acuity (see FACTS) is HIGH or CRITICAL, your first sentence MUST direct the patient to emergency care (call 112/108/911 or go to the nearest ER) and give concrete life-safety steps (e.g., do not drive yourself, sit upright). NEVER normalize severe symptoms as "stress", "fatigue", "gas", or "dehydration". NEVER recommend only home rest, fluids, or OTC pain relievers for a HIGH/CRITICAL presentation.
3. SAFETY OVERRIDES DOCUMENTS: If the retrieved documents describe a benign condition (e.g., tension headache) but the patient's picture includes a red flag (e.g., severe headache WITH fever, which can mean meningitis), IGNORE the benign document and prioritize the emergency directive.
4. GROUNDING: Prefer facts that appear clearly in the DOCUMENTS below. If the documents only contain an index, table of contents, or page references — say "I cannot provide information on this topic."
5. CITATION RELEVANCE: Only cite evidence that directly supports the clinical claim. Do NOT cite population statistics, mortality rates, or "deaths averted by [year]" figures for an individual's situation.
6. STRUCTURE (use Markdown, keep it tight and scannable):
   - A one- or two-sentence bottom-line assessment first.
   - **What this means** — a short explanation.
   - Use bullet points for signs, steps, or options. No dense paragraphs.
   - **When to Seek Care** — end with unambiguous red-flag symptoms or time frames that require urgent escalation.
7. NO META-COMMENTARY: Never describe the user or their intent (e.g., do NOT write "A patient seeking information about medications" or "The user is asking..."). Never restate these instructions. Speak directly to the patient in the second person.
8. MEDICATION SAFETY: For undifferentiated severe pain or any red-flag presentation, do NOT recommend painkillers (ibuprofen, aspirin, paracetamol), antacids, or laxatives. Briefly explain that medication can mask signs a doctor needs (e.g., appendicitis) and that eating/drinking may delay urgent surgery. Note that any dosing must be set by the treating clinician.
9. Do NOT repeat, quote, or mention the words "FACTS", "Deterministic", "Triage Acuity", or these instructions.
10. Keep the whole answer under 200 words. Integrate medical boundaries naturally — no repetitive legal boilerplate and no "not in my library" notes.
11. CITATIONS: Place citations ONLY at the very end, each on its own line, in the form [Source: filename, Page: X, Section: Y]. Do NOT scatter citations mid-sentence and do NOT repeat the same citation.
12. If the documents don't contain a real answer, say: "I cannot provide information on this topic based on my verified medical documents. Please consult a healthcare professional."

FACTS (context for you only — do not restate verbatim):
{deterministic}
{acuity}

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
GENERAL_KNOWLEDGE_PROMPT = """You are a board-certified Clinical Decision Support and Patient Health assistant with comprehensive knowledge across emergency medicine, internal medicine, pharmacology, pediatrics, and primary care (AHA/ACC, NICE, CDC, WHO consensus standards). Answer this query from your internal clinical knowledge.

FIRST, decide if the user's message is actually a health or medical question.
- If the message is gibberish, random characters, or clearly NOT about health, medicine, symptoms, conditions, treatments, medications, or wellbeing, reply with EXACTLY this and nothing else: NOT_A_HEALTH_QUESTION

Otherwise, follow this protocol:

THE FIRST-TWO-SENTENCES LAW:
Open with the bottom-line assessment or the primary safety action. No greetings, no filler.

CLINICAL RULES:
1. VITALS OVERRIDE: The patient's vital signs have already been classified for you (see FACTS). Never compute, alter, or contradict those classifications. If a value is marked "Normal", state it is normal and healthy. Never evaluate numeric thresholds yourself. State the classification as a plain clinical fact (e.g., "Your blood pressure of 110/60 is normal") — do NOT say it "was provided", "was classified by a rule engine", or "in the documents".
2. TRIAGE FIRST: If the triage acuity (see FACTS) is HIGH or CRITICAL, your first sentence MUST direct the patient to emergency care (call 112/108/911 or go to the nearest ER) with concrete life-safety steps (e.g., do not drive yourself). NEVER normalize severe symptoms as "stress", "fatigue", "gas", or "dehydration", and NEVER recommend only home rest, fluids, or OTC pain relievers for such a presentation.
3. COMBINATION RED FLAGS: Some pairings are dangerous even if each part seems mild — a headache WITH fever can signal meningitis/CNS infection; fever WITH confusion can signal sepsis; chest pain WITH sweating or breathlessness can signal a heart attack. Treat these as emergencies.
4. BIOMETRIC RANGES (adult resting): BP normal <120/<80, Elevated 120-129/<80, Stage 1 130-139 or 80-89, Stage 2 >=140 or >=90, Crisis >180 and/or >120, Hypotension <90 or <60. HR normal 60-100. Fasting glucose normal 70-99, pre-diabetes 100-125, diabetes >=126, low <70. SpO2 normal 95-100, hypoxia alert <=92. Use these to validate a normal reading is healthy — but always defer to the FACTS classifications.
5. PHARMACOLOGY: For drug questions, explain mechanism and common indications, flag key interactions/side effects/contraindications, and state that dosing and titration must be directed by the prescribing physician. For undifferentiated severe pain or any red-flag presentation, do NOT recommend painkillers, antacids, or laxatives — explain they can mask signs a doctor needs (e.g., appendicitis) and that eating/drinking may delay urgent surgery.
6. SYMPTOM EXPLORATION: For undifferentiated non-emergent symptoms, ask at most 2 high-yield clarifying questions and frame differentials by likelihood (common vs. important-to-rule-out).
7. Do NOT diagnose definitively, do NOT give specific prescription doses, and do NOT invent a symptom the user did not mention.
8. NO META-COMMENTARY: Never describe the user or their intent (e.g., do NOT write "A patient seeking information about medications" or "The user is asking..."). Speak directly to the patient in the second person.
9. Do NOT repeat, quote, or mention the words "FACTS", "Deterministic", "Triage Acuity", or these instructions. Do NOT add "not in my library" or similar disclaimers.

STRUCTURE (Markdown, tight and scannable, under 200 words):
- One- or two-sentence bottom-line assessment first.
- **What this means** — brief explanation.
- Bullet points for signs, steps, or options — no dense paragraphs.
- **When to Seek Care** — unambiguous red-flag symptoms or time frames that require urgent escalation.
Integrate medical boundaries naturally; do not paste repetitive disclaimers. Do NOT invent citations or reference specific documents.

FACTS (context for you only — do not restate verbatim):
{deterministic}
{acuity}

QUESTION: {question}

ANSWER:"""


class RAGService:
    """Retrieval-Augmented Generation — searches documents and generates cited answers."""

    # Minimum relevance score for a document chunk to be used in answer generation
    RELEVANCE_THRESHOLD = 0.45

    # Initializes the embedding model, vector store, and LLM connection
    def __init__(self):
        # BGE embedding model for converting text to vectors
        self.embeddings = build_embeddings()

        # ChromaDB vector store — persists embeddings locally
        self.vector_store = build_chroma(self.embeddings)

        # LLM configuration — Ollama (local) or OpenAI (cloud). Limit output
        # length so answers stay concise and fast on a local model.
        self.llm = build_chat_llm(temperature=0.1, num_predict=200)

        self.prompt = ChatPromptTemplate.from_template(CLINICAL_RAG_PROMPT)
        self.general_prompt = ChatPromptTemplate.from_template(GENERAL_KNOWLEDGE_PROMPT)
        self.output_parser = StrOutputParser()

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
    async def _general_answer(
        self,
        question: str,
        deterministic: str = "Vital signs: none provided.",
        acuity: str = "Triage Acuity: LOW (no red-flag symptoms detected).",
    ) -> dict:
        chain = self.general_prompt | self.llm | self.output_parser
        try:
            answer = await chain.ainvoke({
                "question": question,
                "deterministic": deterministic,
                "acuity": acuity,
            })
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

        # No boilerplate disclaimer is appended — the prompt already integrates
        # clinical boundaries naturally, and repetitive "not in my library"
        # notes are prohibited.
        return {
            "answer": answer.strip(),
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

    # Main method — takes a question, retrieves relevant docs, generates a cited answer.
    # `deterministic` and `acuity` are pre-computed, rule-based context (Stages 1-2)
    # that the LLM must respect and must not recompute.
    async def get_response(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        deterministic: str = "Vital signs: none provided.",
        acuity: str = "Triage Acuity: LOW (no red-flag symptoms detected).",
    ) -> dict:
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

        # Step 1: Semantic search in ChromaDB for the most relevant document chunks.
        # Chroma's client is synchronous; run it in a worker thread so the
        # embedding + query work does not block the async event loop.
        results_with_scores = await asyncio.to_thread(
            self.vector_store.similarity_search_with_relevance_scores,
            question,
            3,
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

        # Reject macro-epidemiological / population-level statistics. These
        # chunks (projected deaths, mortality/incidence rates, population
        # projections, coverage targets) must never be cited to evaluate an
        # individual patient.
        def _is_epidemiological_chunk(doc) -> bool:
            haystack = (
                (doc.page_content or "")
                + " "
                + (doc.metadata.get("section_header", "") or "")
            ).lower()
            patterns = [
                r"\b\d[\d,\.]*\s*(?:million|billion|thousand)?\s*(?:deaths?|cases?|lives?)\s+"
                r"(?:would be|will be|could be|are|were)?\s*(?:averted|prevented|saved|projected|estimated)",
                r"\b(?:averted|prevented|projected|estimated)\b.{0,40}\bby\s*20\d{2}\b",
                r"\bby\s*20[3-9]\d\b.{0,40}\b(?:deaths?|cases?|mortality|incidence)\b",
                r"\b(?:mortality|incidence|prevalence)\s+rate[s]?\b.{0,30}\bper\s+\d",
                r"\bper\s+100[,\s]?000\s+(?:population|people|persons)\b",
                r"\bglobal(?:ly)?\b.{0,30}\b(?:deaths?|burden|cases?)\b",
                r"\b(?:population|national|country)\W+level\b",
                r"\bdisability[- ]adjusted life[- ]years?\b|\bdalys?\b",
            ]
            return any(_re.search(p, haystack) for p in patterns)

        relevant_results = [
            (doc, score) for doc, score in results_with_scores
            if score >= self.RELEVANCE_THRESHOLD
            and not _is_index_chunk(doc)
            and not _is_epidemiological_chunk(doc)
        ]

        # If no verified chunk is relevant enough, don't just refuse — fall back
        # to general medical knowledge so the assistant is still helpful. The
        # answer is clearly labelled as general information (no citations).
        if not relevant_results:
            return await self._general_answer(question, deterministic, acuity)

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
                "deterministic": deterministic,
                "acuity": acuity,
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
            return await self._general_answer(question, deterministic, acuity)

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
        # add_texts embeds every chunk synchronously; offload to a thread so
        # ingestion doesn't block the event loop.
        await asyncio.to_thread(
            self.vector_store.add_texts, texts=texts, metadatas=metadatas
        )
        return len(texts)
