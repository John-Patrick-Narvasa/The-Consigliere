# src/agent/graph.py
import os
from google import genai
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from src.agent.state import AgentState
from src.agent.nodes import retrieve_context, advice_node, procedure_node, system_node

ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def route_by_intent(state: AgentState) -> str:
    """
    Conditional Routing Edge: Analyzes user message context and 
    returns target transition keys.
    """
    print(" -> Router: Assessing conversation metadata trajectory mapping...")
    last_message = state["messages"][-1].content
    
    classification_prompt = f"""
    Analyze the incoming user request and determine the primary interaction type needed.
    
    User Request: "{last_message}"
    
    Classification Schema:
    - Return 'procedure' if they want a chronological sequence, micro-steps, checklist, or a direct todo list plan.
    - Return 'system' if they want a system blueprint, framework diagram, habit loop model, or repeatable workflow setup.
    - Return 'advice' if they are asking a high-level strategic question, evaluating a situation, or seeking general guidance.
    
    CRITICAL Rule: Output ONLY one string matching either 'advice', 'procedure', or 'system'. Do not append punctuation or explanations.
    """
    
    res = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=classification_prompt
    )
    
    intent = res.text.strip().lower()
    print(f"  ├─► Detected Target Strategy Node: '{intent}'")
    
    if intent in ["advice", "procedure", "system"]:
        return intent
    return "advice" # Resilient safety default fallback

# =====================================================================
# SYSTEM BUILDER ENGINE SETUP
# =====================================================================
workflow = StateGraph(AgentState)

# Wire up structural nodes
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("advice", advice_node)
workflow.add_node("procedure", procedure_node)
workflow.add_node("system", system_node)

# Set up initialization transitions
workflow.add_edge(START, "retrieve_context")

# Connect the retrieval layer to your custom routing rules
workflow.add_conditional_edges(
    "retrieve_context",
    route_by_intent,
    {
        "advice": "advice",
        "procedure": "procedure",
        "system": "system"
    }
)

# Connect execution nodes to completion endpoints
workflow.add_edge("advice", END)
workflow.add_edge("procedure", END)
workflow.add_edge("system", END)

# Compile final graph package
compiled_graph = workflow.compile()