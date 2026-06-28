# The Consigliere: Agent Subsystem Technical Documentation

This documentation serves as an architectural blueprint and engineering reference for the LangGraph-powered orchestration layer of **The Consigliere** system.

---

## 1. Step-by-Step System Architecture

The Agent Subsystem is engineered as a stateful, directed acyclic graph (DAG) runtime system using LangGraph. Instead of relying on a single, fragile linear prompt, it isolates context compilation, dynamic intent routing, and custom layout generation into independent computational nodes that read and mutate a centralized state ledger.

### Complete Architecture & Control Flow Mapping

The following diagram maps the entire multi-threaded route configuration from the initial user request trigger to the structural message return output:

```text
                                 [ USER INPUT ]
                                        │
                                        ▼
                                  ┌───────────┐
                                  │  (START)  │
                                  └─────┬─────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │     retrieve_context      │
                          │   (Pinecone Embedding)    │
                          └─────────────┬─────────────┘
                                        │
                                        ├─► [AgentState Updates]:
                                        │    • context: [Diverse List of Fragments]
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │      route_by_intent      │
                          │   (Intent Classifier)     │
                          └─────────────┬─────────────┘
                                        │
                                        ├─► [AgentState Updates]:
                                        │    • intent: "advice" | "procedure" | "system"
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             │                          │                          │
    (Route: 'advice')          (Route: 'procedure')        (Route: 'system')
             ▼                          ▼                          ▼
  ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
  │    advice_node     │     │   procedure_node   │     │    system_node     │
  │ (Strategic Prompt) │     │ (Step-by-Step Mod) │     │ (Framework Blueprint)│
  └──────────┬─────────┘     └──────────┬─────────┘     └──────────┬─────────┘
             │                          │                          │
             │                          ▼                          │
             └──────────────────────► ┌───┐ ◄──────────────────────┘
                                      │END│
                                      └───┘
                                        │
                                        ▼
                               [ STRUCTURAL OUT ]
```

---

### The State Mutation Lifecycle

The graph operates by passing a single transactional memory block called `AgentState` from node to node. Each step intercepts the current snapshot of data, processes it, and appends its updates back to the schema.

Here is how the data structure morphs at each micro-step of execution:

```text
──────────────────────────────────────────────────────────────────────────────────────────────────
STAGE 01: GRAPH ENTRY
──────────────────────────────────────────────────────────────────────────────────────────────────
 State Initial Value:
 {
     "messages": [ HumanMessage(content="Build me a workflow routine...") ],
     "context": [],
     "intent": ""
 }
                                 │
                                 ▼
──────────────────────────────────────────────────────────────────────────────────────────────────
STAGE 02: POST-RETRIEVAL NODE
──────────────────────────────────────────────────────────────────────────────────────────────────
 State Mutated To:
 {
     "messages": [ HumanMessage(content="Build me a workflow routine...") ],
     "context": [
         {"source": "Atomic Habits", "page": 42, "text": "Habit stacking relies on..."},
         {"source": "Building a Second Brain", "page": 112, "text": "The daily review structure..."}
     ],
     "intent": ""
 }
                                 │
                                 ▼
──────────────────────────────────────────────────────────────────────────────────────────────────
STAGE 03: POST-ROUTER CONDITIONAL EDGE
──────────────────────────────────────────────────────────────────────────────────────────────────
 State Mutated To:
 {
     "messages": [ HumanMessage(content="Build me a workflow routine...") ],
     "context": [ ...Fragments Cache... ],
     "intent": "procedure"  ◄── [Determined pathway branch value]
 }
                                 │
                                 ▼
──────────────────────────────────────────────────────────────────────────────────────────────────
STAGE 04: EXECUTION TARGET OUTPUT (FINAL)
──────────────────────────────────────────────────────────────────────────────────────────────────
 State Mutated To:
 {
     "messages": [
         HumanMessage(content="Build me a workflow routine..."),
         AIMessage(content="To establish a routine: 1. Habit Stack [Atomic Habits, P. 42]...") ◄── [Appended]
     ],
     "context": [ ...Fragments Cache... ],
     "intent": "procedure"
 }
──────────────────────────────────────────────────────────────────────────────────────────────────
```

---

### Phase Breakdown

1. **Context Enrichment Layer (`retrieve_context`):**

* **Action:** Captures the final element in the `messages` list, requests a 1,024-dimension embedding array from `gemini-embedding-001`, and queries your live Cloud Pinecone cluster.
* **Diversification Guard:** Instead of blindly returning the closest vectors, it intercepts the top 8 blocks and filters them via a strict token cap limit per source book. This stops highly repetitive vocabulary sections from a single book from consuming all available context space.

2. **Classification Routing Logic (`route_by_intent`):**

* **Action:** Evaluates the input structure using a lightweight, fast text classification instruction system on `gemini-2.5-flash`.
* **Behavior:** Outputs a clean, single token match mapping to your exact edge paths (`advice`, `procedure`, or `system`). If an unpredictable syntax exception occurs, a defensive system fallback automatically overrides the trace and forces an `advice` trajectory route.

3. **Specialized Persona Execution (`advice` | `procedure` | `system`):**

* **Action:** The designated node combines your core base *Consigliere* identity instructions with custom formatting extensions loaded directly from `prompts.py`.
* **Output:** Compiles the total message string using structured text layout conventions and explicit numerical page citations before closing the pipeline at the `END` state boundary marker.

---

## 2. Functional Reference Registry

Every operational unit within `src/agent/` is built for isolated extensibility. Use this guide to safely adjust or scale the agent's behavior.

| Function Name        | Code Location | Primary Responsibility                                                                   | Modification Levers (What to Edit)                                                                                                                             |
| -------------------- | ------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `retrieve_context` | `nodes.py`  | Generates text embeddings and fetches matching source fragments from Pinecone.           | Modify`top_k` to alter context volume. Adjust the grouping cap (`seen_sources.get(src, 0) >= 3`) to tweak multi-source diversity.                          |
| `route_by_intent`  | `graph.py`  | Inspects current conversational context and chooses the optimal graph execution pathway. | Tweak the classification rules or add new classification terms (e.g., 'code', 'analysis') to map to new downstream graph routes.                               |
| `advice_node`      | `nodes.py`  | Handles high-level strategic reasoning, risk assessment, and conceptual evaluation.      | Modify`ADVICE_PROMPT_EXTENSION` in `prompts.py` to change the underlying analytical framework.                                                             |
| `procedure_node`   | `nodes.py`  | Converts abstract strategy into distinct chronologically sequenced todo lists.           | Modify`PROCEDURE_PROMPT_EXTENSION` in `prompts.py` to adjust step formats, constraints, or milestone markers.                                              |
| `system_node`      | `nodes.py`  | Generates visual architectural loops, mental systems, and recursive frameworks.          | Modify`SYSTEM_PROMPT_EXTENSION` in `prompts.py` to enforce different visualization styles or change the diagram engines (e.g., switching from Mermaid.js). |

---

## 3. Subsystem Problem Ledger

This ledger compiles identified engineering bugs, cognitive limitations, and scaling issues discovered during implementation. Use this to monitor system reliability.

### Syntax & Structural Exceptions

* **Tuple Unpacking Mismatch:** Refactoring `extract_and_chunk_pdf` to return a tuple `(chunks_list, end_page)` caused structural breaks in modules expecting a single direct reference. Fixed by explicit destructuring: `chunks_list, _ = extract_and_chunk_pdf(...)`.
* **Iterable Unpacking ValueError:** In the multi-book loading configuration loop, attempting to unpack lists directly (`for path, name in (paths, names)`) caused runtime system crashes. Resolved by using `zip(paths, names)`.

### Algorithmic & Logical Skewing

* **Context Vector Starvation:** Naive top-k search allowed highly repetitive keyword-dense sections from a single book to monopolize all text slots. This completely shut out relevant text frames from other source material. Resolved by increasing lookup width (`top_k=8`) and adding a deduplication threshold loop inside `nodes.py`.
* **Unextractable Page Short-Circuits:** Enforcing state saves when reading blank, visual-only, or diagram-heavy page sets inadvertently forced loops to exit mid-book with a `True` value. Resolved by forcing a `False` response unless `end_page >= total_pages`.

### Program Scalability & API Constraints

* **Gemini Quota Exhaustion (Code 429):** Free-tier execution limits allow up to 1,000 requests per day. High-speed indexing quickly runs through this allocation. Resolved by adding string searches inside the `ClientError` block to catch `"day"` limits and exit gracefully, preserving checkpoints.
* **Pinecone Metric Host Drops:** Instantiating the vector store interface index without explicit host references can cause unexpected thread timeouts during long synchronization jobs. Resolved by forcing the engine to validate environment strings directly via `INDEX_HOST`.

---

## 4. Developer Onboarding & Subsystem Testing Guide

Follow this guide to initialize the isolated agent subsystem environment and run integration verification sweeps without launching the full web application layer.

### Phase 1: Environment Verification

Ensure your root configuration parameters are securely set up in `.env`:

```bash
GEMINI_API_KEY="your_api_key_here"
PINECONE_API_KEY="your_pinecone_key_here"
PINECONE_INDEX_HOST="https://your-index-host-url.pinecone.io"
```

### Phase 2: Execution of Isolated Diagnostic Suite

Execute the agent test runner tool from your terminal. This script initializes a mock session thread ID, mocks an engineering scenario query, pushes it through the routing graph, and logs the classification results.

```bash
# Ensure your virtual environment is active
# Run the module execution command from the workspace root directory
python -m src.agent.test_agent
```

### Expected Success Output Signatures

When running correctly, the runtime thread must match these system trace logs exactly:

```text
--- STARTING AGENTIC BLUEPRINT INTEGRATION AUDIT ---

User Input: 'Build me a morning workflow routine using atomic habits structure'
 -> Execution Layer: Fetching grounding context from Pinecone cluster...
 -> Router: Assessing conversation metadata trajectory mapping...
   ├─► Detected Target Strategy Node: 'procedure'
 -> Node Execution: Initiating Step-by-Step Task Decomposition Node Protocol.

============================================================
CONSIGLIERE AGENT RESPONSE:
============================================================
[Verified grounded advice with trailing source book page citations]
============================================================
```
