# src/agent/state.py
from typing import TypedDict, Annotated, List
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    The structural state memory for The Consigliere framework.
    """
    # Tracks entire multi-turn conversation thread seamlessly
    messages: Annotated[List[AnyMessage], add_messages]
    # Stores raw structural source text data fetched during execution
    context: List[dict]
    intent: str