# The Consigliere System

This production-grade reference manual serves as the primary technical specification handbook for **The Consigliere**—a context-grounded, stateful Retrieval-Augmented Generation (RAG) orchestration engine. The system converts tactical literary paradigms (such as Sun Tzu’s *The Art of War* and Tiago Forte’s *Building a Second Brain*) into real-time, structured operational advice.

---

## 1. Global System Blueprint & Data Lifecycle

The system operates across three distinct operational layers: an **Ingestion Pipeline** (batch processing, data sanitization, vector extraction), an **Orchestration Brain** (stateful directed acyclic graph reasoning), and a **Presentation Interface** (REST API gateway and asynchronous UI workspace).

```text
  [ LOCAL STORAGE ]               [ ORCHESTRATION LAYER ]             [ USER INTERFACE ]
  
   +--------------+                  +------------------+             +----------------+
   |  Local PDFs  |                  |  LangGraph Core  |             |  Streamlit UI  |
   +-------+------+                  +--------+---------+             +--------+-------+
           |                                  ^                                |
           | (PyMuPDF / RegEx)                | (State Memory)                 | (User Query)
           ▼                                  ▼                                ▼
   +-------+------+                  +--------+---------+             +--------+-------+
   |  parser.py   |                  |    nodes.py      |             |   FastAPI Gateway|
   +-------+------+                  +--------+---------+             +--------+-------+
           |                                  ^                                |
           | (Text Chunks)                    | (JSON Payload)                 | (Rest Target)
           ▼                                  ▼                                ▼
   +-------+------+   (1,024-Dim)    +--------+---------+             +--------+-------+
   |  ingest.py   +----------------->| Pinecone Cluster |<------------+   main.py      |
   +--------------+   (Gemini Embed) +------------------+ (Vector Look) +----------------+
```

---

## 2. Directory Tree Map Topology

```text
TheConsigliere/
│
├── data/                       # Local file repository for binary source literature
│   ├── art_of_war.pdf
│   └── atomic_habits.pdf
│
├── src/
│   ├── __init__.py
│   │
│   ├── ingestion/             # The Processing Pipeline
│   │   ├── __init__.py        # Continuous synchronization pipeline sequence
│   │   ├── parser.py          # Low-level text extraction and character filtering
│   │   └── ingest.py          # Throttled embedding client and Pinecone synchronization
│   │
│   ├── agent/                 # The Intelligence Component
│   │   ├── __init__.py
│   │   ├── graph.py           # LangGraph workflow structure and router configuration
│   │   ├── nodes.py           # Specialized persona nodes (Advice, Procedure, System)
│   │   ├── state.py           # Shared transactional state schemas
│   │   └── prompts.py         # Base operational identity configurations
│   │
│   └── api/                   # The Access Gate
│       ├── __init__.py
│       └── main.py            # FastAPI endpoints and payload definitions
│
├── .env                       # Local secrets management container
├── requirements.txt           # Consolidated external software dependencies
└── app.py                     # Reactive Streamlit presentation layer interface
```

---

## 3. Subsystem Deep-Dive Matrix

### 3.1. Data Ingestion Subsystem

The data ingestion pipeline utilizes an incremental, page-bounded batch architecture to convert unstructured local PDF documents into structured high-dimensional vector spaces.

* **Extraction Safeguards:** Rather than running open-ended loops, page indexing bounds calculations are evaluated dynamically using a restrictive lookahead formula to eliminate out-of-bounds risks:

$$
\text{end\_page} = \min(\text{start\_page} + \text{max\_pages\_to\_process} - 1, \text{total\_pages})
$$

* **Sanitization Filters:** Documents are scrubbed of noise using low-level regular expressions that intercept unprintable Control Characters: `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]`.
* **Checkpoint Persistence:** All operations track state inside `ingestion_state.json`. If a run encounters a transient network crash or hitting a rate limit, it saves state and can cleanly resume processing from the exact page index.

### 3.2. Agent Orchestration Subsystem (LangGraph)

The core logical engine bypasses standard brittle prompts, isolating individual tasks into structured nodes operating inside a Directed Acyclic Graph (DAG).

* **State Ledger Transaction Lifecycle:** A centralized transactional memory block (`AgentState`) tracks context mutations as messages move through graph pathways.
* **Context Starvation Deflection Guard:** To prevent an exceptionally dense source file from monopolizing all available token context windows during top-k vector checks, a deduplication threshold loop enforces strict per-book limits inside `nodes.py`.
* **Dynamic Intent Routing:** Processing flows through a dedicated text classifier model run on `gemini-2.5-flash`. The model outputs exact token route matches (`advice`, `procedure`, or `system`), with an error fallback that redirects back to the standard strategic path if needed.

### 3.3. API Network Routing Layer

The API layer acts as an asynchronous network interface. It uses FastAPI to receive requests, runs inputs through validation schemas via Pydantic, calls the active LangGraph worker instances, and maps responses into organized JSON schemas.

* **Thread Execution Isolation:** To protect async system loops from blocking during long-running vector evaluations, graph tasks are dispatched directly into separate background worker threads using internal thread pool structures.

### 3.4. Streamlit Interactive Client Space

The system's UI provides a fast, reactive front-end dashboard that connects directly to the API server gateway. It tracks unique user session IDs via UUID generation, displays active message blocks, and highlights the agent's sourcing by rendering citation arrays cleanly beneath each response box.

---

## 4. Production Fault-Tolerance & Failure Modes

| Failure Vector                                   | Core Root Cause                                                                                  | Implemented Engineering Resolution                                                                                                                                                           |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **HTTP 429 Error:** `RESOURCE_EXHAUSTED` | Exceeded 100 requests-per-minute ceiling on free-tier Gemini instances.                          | Combined a proactive`time.sleep(3.5)` loop step with an exception handler that pauses execution for 65 seconds when a 429 occurs.                                                          |
| **Quota Exhaustion:** Infinite Sleep Loops | Repeated short sleep cycles fail when hitting the 1,000 requests-per-day volume ceiling.         | Enforced a secondary string pattern analysis check (`"day"` / `"perday"`). When triggered, the system saves its current progress checkpoint and executes a clean shutdown (`exit(0)`). |
| **Context Monopolization**                 | Dense keyword sections from a single book push out other helpful book references.                | Broadened the lookup width to`top_k=8` and added an explicit per-source volume filter to balance citation variety.                                                                         |
| **Empty Chunk Processing**                 | Processing blank or image-only page ranges generated empty text arrays that broke state engines. | Swapped out brittle short-circuit code for lookahead checks that pass execution forward without exiting unless`end_page >= total_pages`.                                                   |

---

## 5. Developer Onboarding & Deployment Playbook

### Phase 1: Environment Isolation & Provisioning

Initialize your local runtime environment and dependencies from your project workspace root directory:

```bash
# Provision isolated execution container
python -m venv venv

# Activate local environment bindings (Windows Shell)
venv\Scripts\activate
# Alternative: Activate environment bindings (macOS / Linux Bash)
source venv/bin/activate

# Force pipeline dependency manager upgrades
python -m pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

### Phase 2: Configuration Mapping (`.env`)

Generate a `.env` configuration file at the root level of your directory structure:

```bash
GEMINI_API_KEY="your_native_gemini_api_key"
PINECONE_API_KEY="your_pinecone_cluster_key"
PINECONE_INDEX_HOST="https://your-target-index-hash.pinecone.io"
```

### Phase 3: Executing Verification & Initialization Diagnostics

Run individual validation commands in sequence to verify that each stage of the system architecture works correctly:

```bash
# 1. Test binary file text extraction and chunk segmentation
python -m src.ingestion.parser

# 2. Synchronize your local documents repository with your Cloud Pinecone Index
python -m src.ingestion.ingest

# 3. Verify LangGraph integration and local agent routing logic
python -m src.agent.test_agent
```

### Phase 4: Production Service Launch

To start the complete application interface, run the server and client scripts in separate terminal instances:

```bash
# Terminal App 1: Launch the FastAPI Gateway Router
uvicorn src.api.main:app --reload --port 8000

# Terminal App 2: Launch the Streamlit Frontend Web App
streamlit run app.py
```
