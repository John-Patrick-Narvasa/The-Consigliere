# test_agent.py
from langchain_core.messages import HumanMessage
from src.agent.graph import compiled_graph

def run_local_agent_audit():
    print("--- STARTING AGENTIC BLUEPRINT INTEGRATION AUDIT ---")
    
    # Mocking single-turn interaction state sequence tracking
    config = {"configurable": {"thread_id": "test_session_01"}}
    
    # Triggering query targeted directly at testing the SYSTEM node classification
    test_query = "Build me a morning workflow routine using atomic habits structure"
    
    print(f"\nUser Input: '{test_query}'")
    initial_inputs = {"messages": [HumanMessage(content=test_query)]}
    
    output_state = compiled_graph.invoke(initial_inputs, config)
    
    final_message = output_state["messages"][-1].content
    print("\n" + "="*60)
    print("CONSIGLIERE AGENT RESPONSE RESPONSE:")
    print("="*60)
    print(final_message)
    print("="*60)

if __name__ == "__main__":
    run_local_agent_audit()