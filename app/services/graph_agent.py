

from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


class HealthAgentState(TypedDict):
    
    question: str                  
    question_type: str             
    context: str                   
    answer: str                    
    reading_level: str             
    is_safe: bool                  


def classify_question(state: HealthAgentState) -> dict:
    
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=settings.OPENAI_API_KEY)

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
    
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, api_key=settings.OPENAI_API_KEY)

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


health_agent = create_health_agent_graph()
