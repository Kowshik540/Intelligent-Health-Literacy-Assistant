"""
Jargon Simplifier — Rewrites clinical medical text into plain language.
Uses an LLM to convert terms like "Myocardial Infarction" to "Heart Attack"
while preserving all citations and factual accuracy.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.services.llm_factory import build_chat_llm


# Prompt template that instructs the LLM to simplify without adding new information
SIMPLIFIER_PROMPT = """Rewrite the following medical answer in clear, plain English for a general adult reader. Keep it accurate, professional, and just as scannable.

STRICT RULES:
1. Only rephrase what is written. Do NOT add any new facts, examples, risks, or conditions that are not in the original.
2. For medical terms, add the plain meaning in parentheses. Example: "Hypertension (high blood pressure)".
3. PRESERVE THE STRUCTURE: keep the same Markdown formatting — the opening bottom-line sentence(s), any **bold headings** (such as "What this means" and "When to Seek Care"), and every bullet point. Rewrite the text inside them; do not collapse them into one paragraph.
4. Keep ALL [Source: ...] citations exactly as they are, on their own line.
5. Keep any emergency directive (call 112/108/911, go to the ER, do not drive) in the FIRST sentence, exactly as urgent as the original.
6. Use short, clear sentences and a calm, respectful tone. Do NOT use childish comparisons (no "candy", "tummy", etc.).
7. Do NOT add commentary about what you did. Give only the rewritten answer.
8. Keep it the same length or shorter than the original.

ORIGINAL:
{clinical_answer}

PLAIN-LANGUAGE VERSION:"""


class JargonSimplifier:
    """Converts clinical medical language to plain everyday English."""

    # Initializes the LLM connection (same model as RAG, but higher temperature for natural language)
    def __init__(self):
        self.llm = build_chat_llm(temperature=0.1)

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
