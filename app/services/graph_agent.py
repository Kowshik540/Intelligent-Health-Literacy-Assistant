"""
Optional LangGraph agent (classify -> generate -> safety check). Built lazily
via get_health_agent() so importing this module doesn't spin up an LLM.
"""

from typing import Literal, Optional, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

from app.services.llm_factory import build_chat_llm


class HealthAgentState(TypedDict):
    question: str
    question_type: str
    context: str
    answer: str
    reading_level: str
    is_safe: bool


def classify_question(state: HealthAgentState) -> dict:
    llm = build_chat_llm(temperature=0)
    if llm is None:
        return {"question_type": "general"}

    prompt = ChatPromptTemplate.from_template(
        "Classify this health question into ONE category: "
        "'symptom', 'medication', 'condition', 'lifestyle', or 'general'.\n"
        "Question: {question}\n"
        "Category (one word only):"
    )

    chain = prompt | llm | StrOutputParser()

    try:
        result = chain.invoke({"question": state["question"]})
        question_type = result.strip().lower()
    except Exception:
        question_type = "general"

    return {"question_type": question_type}


def route_question(state: HealthAgentState) -> Literal["generate_answer"]:
    return "generate_answer"


def generate_answer(state: HealthAgentState) -> dict:
    llm = build_chat_llm(temperature=0.3)
    if llm is None:
        return {
            "answer": (
                "No language model is configured. Set USE_OLLAMA=True with a "
                "running Ollama server, or provide an OPENAI_API_KEY."
            ),
            "is_safe": True,
        }

    prompt = ChatPromptTemplate.from_template(
        "You are a health literacy assistant. The question type is: {question_type}\n\n"
        "Context from medical documents:\n{context}\n\n"
        "Question: {question}\n\n"
        "Explain in simple language (6th grade reading level). "
        "If context is empty, use general knowledge but note you don't have specific documents.\n"
        "Answer:"
    )

    chain = prompt | llm | StrOutputParser()

    try:
        answer = chain.invoke({
            "question_type": state.get("question_type", "general"),
            "context": state.get("context", "No documents available."),
            "question": state["question"],
        })
    except Exception as e:
        answer = f"I'm sorry, I couldn't process your question. Error: {str(e)}"

    return {"answer": answer, "is_safe": True}


def safety_check(state: HealthAgentState) -> dict:
    answer = state.get("answer", "")

    unsafe_phrases = [
        "you should stop taking",
        "you definitely have",
        "don't see a doctor",
        "ignore your doctor",
    ]

    is_safe = not any(phrase in answer.lower() for phrase in unsafe_phrases)

    if not is_safe:
        return {
            "answer": (
                "I want to help, but I need to be careful with health advice. "
                "Please consult your healthcare provider for personalized guidance."
            ),
            "is_safe": False,
        }

    return {"is_safe": True}


def create_health_agent_graph():
    graph = StateGraph(HealthAgentState)

    graph.add_node("classify_question", classify_question)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("safety_check", safety_check)

    graph.set_entry_point("classify_question")
    graph.add_edge("classify_question", "generate_answer")
    graph.add_edge("generate_answer", "safety_check")
    graph.add_edge("safety_check", END)

    return graph.compile()


# Lazily-built, cached compiled graph. Import stays side-effect free.
_health_agent = None


def get_health_agent():
    """Return the compiled health-agent graph, building it on first use."""
    global _health_agent
    if _health_agent is None:
        _health_agent = create_health_agent_graph()
    return _health_agent
