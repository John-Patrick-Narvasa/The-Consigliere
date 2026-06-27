# src/agent/nodes.py
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pinecone import Pinecone
from langchain_core.messages import AIMessage

from src.agent.state import AgentState
from src.agent.prompts import (
    CONSIGLIERE_SYSTEM_BASE,
    ADVICE_PROMPT_EXTENSION,
    PROCEDURE_PROMPT_EXTENSION,
    SYSTEM_PROMPT_EXTENSION
)

load_dotenv()

# Initialize localized clients for runtime transformations
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(host=os.getenv("PINECONE_INDEX_HOST"))

def retrieve_context(state: AgentState) -> dict:
    """
    Extracts the latest user input, embeds it, and grabs the top 4 matched text blocks.
    """
    print(" -> Execution Layer: Fetching grounding context from Pinecone cluster...")
    last_user_message = state["messages"][-1].content
    
    # Generate matching 1024-dimensional embedding
    res = ai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=last_user_message,
        config=types.EmbedContentConfig(output_dimensionality=1024)
    )
    query_vector = res.embeddings[0].values
    
    # Extract matched vectors from cloud index
    query_results = index.query(
        vector=query_vector,
        top_k=4,
        include_metadata=True
    )
    
    fetched_context = []
    if query_results.matches:
        for match in query_results.matches:
            fetched_context.append({
                "source": match.metadata.get("source", "Unknown"),
                "page": int(match.metadata.get("page", 0)),
                "text": match.metadata.get("text", "")
            })
            
    return {"context": fetched_context}

def _generate_consigliere_response(state: AgentState, operational_extension: str) -> dict:
    """
    Helper function to compile context blocks and generate content using Gemini 2.5.
    """
    # Format retrieved document context strings neatly
    context_str = ""
    for idx, doc in enumerate(state["context"], start=1):
        context_str += f"\n[Document Fragment #{idx}]\nSource: {doc['source']}\nPage: {doc['page']}\nContent: {doc['text']}\n"
        
    # Reassemble the chat timeline histories sequentially
    history_str = ""
    for msg in state["messages"]:
        history_str += f"\n{msg.type.capitalize()}: {msg.content}"
        
    # Construct unified instruction runtime matrix
    full_prompt = f"""
    {CONSIGLIERE_SYSTEM_BASE}
    {operational_extension}
    
    ---
    RETRIEVED VERIFIED FACTS:
    {context_str}
    
    ---
    CONVERSATION THREAD HISTORY:
    {history_str}
    
    Consigliere Directive: Provide your definitive answer below ensuring formatting rules are fully preserved.
    """
    
    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt
    )
    
    return {"messages": [AIMessage(content=response.text)]}

def advice_node(state: AgentState) -> dict:
    print(" -> Node Execution: Initiating Strategic Advice Node Protocol.")
    return _generate_consigliere_response(state, ADVICE_PROMPT_EXTENSION)

def procedure_node(state: AgentState) -> dict:
    print(" -> Node Execution: Initiating Step-by-Step Task Decomposition Node Protocol.")
    return _generate_consigliere_response(state, PROCEDURE_PROMPT_EXTENSION)

def system_node(state: AgentState) -> dict:
    print(" -> Node Execution: Initiating System Habit Loop Architecture Node Protocol.")
    return _generate_consigliere_response(state, SYSTEM_PROMPT_EXTENSION)