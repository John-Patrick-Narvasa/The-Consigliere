# app.py
import streamlit as st
import requests
import uuid

# Backend Router Configuration Vectors
FASTAPI_URL = "http://127.0.0.1:8000"
CHAT_ENDPOINT = f"{FASTAPI_URL}/v1/chat"

# --- PAGE CONFIGURATION & WORKSPACE THEMING ---
st.set_page_config(
    page_title="The Consigliere Workspace",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INJECT CUSTOM UX BRANDING STYLES ---
st.markdown("""
    <style>
    .reportview-container { background: #0f1116; }
    .main .block-container { max-width: 1100px; padding-top: 2rem; }
    div[data-testid="stExpander"] {
        background-color: #1a1c23;
        border: 1px solid #2d3139;
        border-radius: 6px;
        margin-top: -10px;
        margin-bottom: 15px;
    }
    .citation-tag {
        display: inline-block;
        background-color: #242936;
        color: #58a6ff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
        margin-right: 5px;
        border: 1px solid #30364d;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE MEMORY STORAGE INITIALIZATION ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR INTERFACE: SYSTEM CONTROL DECK ---
with st.sidebar:
    st.title("💼 The Consigliere")
    st.markdown("### *Strategic Context-Grounded Advisor*")
    st.markdown("---")
    
    st.subheader("Orchestration Parameters")
    st.text_input("Active Session ID", value=st.session_state.session_id, disabled=True)
    
    # Connection Health Status Watcher Loop
    try:
        health_check = requests.get(f"{FASTAPI_URL}/", timeout=2)
        if health_check.status_code == 200:
            st.success("● Gateway Connection Operational")
        else:
            st.warning("⚠️ Gateway Warning Status")
    except requests.exceptions.ConnectionError:
        st.error("❌ Gateway Offline (Port 8000)")

    st.markdown("---")
    st.markdown("""
    ### Grounding Repository Indices
    The advisor synthesizes tactical outputs using direct vector context chunks derived from:
    * `The Art of War` — Sun Tzu
    * `Building a Second Brain` — Tiago Forte
    """)
    
    if st.button("Reset Operational Memory Threads"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# --- MAIN CONVERSATION VIEWPORT ---
st.title("Consigliere Strategic Operation Desk")
st.caption("Stateful multi-book graph execution runtime connected via FastAPI gateway.")
st.markdown("---")

# Render active message thread records from application cache history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        # Pull associated context footprints if they exist for the message block
        if msg["role"] == "assistant" and msg.get("citations"):
            with st.expander("📚 Grounding Context & Source Citations", expanded=False):
                for cit in msg["citations"]:
                    st.markdown(
                        f"<span class='citation-tag'>📖 {cit['source']} — Page {cit['page']}</span>", 
                        unsafe_allow_html=True
                    )

# --- USER PAYLOAD INTERACTION TRIGGER ---
if user_prompt := st.chat_input("Submit tactical situational queries..."):
    
    # 1. Instantly display local human message bubble
    with st.chat_message("user"):
        st.write(user_prompt)
    
    # Commit input payload array record directly into memory cache state
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    # 2. Dispatch async transmission block to FastAPI gateway network interface
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        status_notification = st.info("Invoking multi-threaded advisor routing loops...")
        
        payload = {
            "session_id": st.session_state.session_id,
            "message": user_prompt
        }
        
        try:
            network_response = requests.post(CHAT_ENDPOINT, json=payload, timeout=60)
            status_notification.empty()  # Wipe out the temporary loading status banner
            
            if network_response.status_code == 200:
                data_pack = network_response.json()
                output_text = data_pack.get("response", "Error: No system context generated.")
                citation_array = data_pack.get("citations", [])
                
                # Update viewport display layer layout values
                response_placeholder.write(output_text)
                if citation_array:
                    with st.expander("📚 Grounding Context & Source Citations", expanded=True):
                        for cit in citation_array:
                            st.markdown(
                                f"<span class='citation-tag'>📖 {cit['source']} — Page {cit['page']}</span>", 
                                unsafe_allow_html=True
                            )
                
                # Append finalized output data pack to global transaction history store
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": output_text,
                    "citations": citation_array
                })
                
            else:
                error_body = network_response.json().get("detail", "Unknown routing crash.")
                st.error(f"Execution Error [Code {network_response.status_code}]: {error_body}")
                
        except requests.exceptions.ConnectionError:
            status_notification.empty()
            st.error("Critical Network Interruption: Unable to contact FastAPI on port 8000.")



# TO RUN: uvicorn src.api.main:app --reload --port 8000       streamlit run app.py 