# src/api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

# Import live compiled graph orchestration framework
from src.agent.graph import compiled_graph
from fastapi.concurrency import run_in_threadpool

app = FastAPI(
    title="The Consigliere API", 
    description="Strategic advisor for context-grounded operations.",
    version="1.0"
)

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.get("/")
def health_check():
    return {
        "status": "operational", 
        "agent": "The Consigliere",
        "endpoints": ["/v1/chat"]
    }

@app.post("/v1/chat")
async def chat_with_consigliere(payload: ChatRequest):
    """
    Accepts user requests, routes through intent engines, queries vector indices, 
    and returns tactical advisor statements complete with citation arrays.
    """
    try:
        config = {"configurable": {"thread_id": payload.session_id}}
        
        initial_state = {
            "messages": [HumanMessage(content=payload.message)]
        }
    
        final_state = await run_in_threadpool(compiled_graph.invoke, initial_state, config)
    
        output_message = final_state["messages"][-1].content
        
        citations = [
            {"source": doc["source"], "page": doc["page"]}
            for doc in final_state.get("context", [])
        ]
        
        return {
            "session_id": payload.session_id, 
            "response": output_message,
            "citations": citations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent runtime failure: {str(e)}") 


# TO RUN: uvicorn src.api.main:app --reload --port 8000