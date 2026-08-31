"""
Jargon Simplifier — Rewrites clinical medical text into plain language.
Uses an LLM to convert terms like "Myocardial Infarction" to "Heart Attack"
while preserving all citations and factual accuracy.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


# Prompt template that instructs the LLM to simplify without adding new information
SIMPLIFIER_PROMPT = """Rewrite the following medical answer in plain, simple language that a 6th grader can understand.

RULES:
1. For medical terms, add the plain meaning in parentheses. Example: "Hypertension (High Blood Pressure)"
2. Keep ALL [Source: ...] citations exactly as they are.
3. Break long sentences into shorter ones.
4. Do NOT add new information or commentary.
5. Do NOT add notes about what you did. Just give the simplified answer directly.
6. Keep it concise — same length or shorter than the original.

ORIGINAL:
{clinical_answer}

SIMPLIFIED:"""


class JargonSimplifier:
    """Converts clinical medical language to plain everyday English."""

    # Initializes the LLM connection (same model as RAG, but higher temperature for natural language)
    def __init__(self):
        if settings.USE_OLLAMA:
            from langchain_community.chat_models import ChatOllama
            self.llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.3,
            )
        elif settings.OPENAI_API_KEY:
            self.llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=0.3,
                api_key=settings.OPENAI_API_KEY,
            )
        else:
            self.llm = None

        self.prompt = ChatPromptTemplate.from_template(SIMPLIFIER_PROMPT)
        self.output_parser = StrOutputParser()

    # Takes a clinical answer and returns a plain-language version (falls back to original on error)
    async def simplify(self, clinical_answer: str) -> str:
        if not self.llm:
            return clinical_answer

        chain = self.prompt | self.llm | self.output_parser

        try:
            simplified = await chain.ainvoke({"clinical_answer": clinical_answer})
            return simplified
        except Exception:
            return clinical_answer
