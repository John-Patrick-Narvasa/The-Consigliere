
# The Consigliere: Ingestion Subsystem Technical Documentation

This documentation serves as an architectural blueprint and engineering reference for the stateful, batch-driven data processing and enrichment pipeline of **The Consigliere** system.

---

## 1. Step-by-Step System Architecture

The Ingestion Subsystem is engineered as an incremental, checkpoint-managed processing pipeline. It isolates local binary text extraction, metadata formatting, throttled high-dimensional embedding generation, and vector store transaction operations into a self-recovering architecture that natively tolerates API limits.

### Complete Architecture & Control Flow Mapping

The following diagram traces the system lifecycle, illustrating how raw binary local PDFs are extracted, cleaned, and vectorized before mutating the persistence engine layer:

```text
                       [ LOCAL PDF FILES ]
                               │
                               ▼
                    ┌─────────────────────┐
                    │      parser.py      │ ◄── Reads page slices (e.g., 15 pages)
                    │  (PyMuPDF & RegEx)  │
                    └──────────┬──────────┘
                               │ Generates parsed text chunks
                               ▼
                    ┌─────────────────────┐     Validates ingestion_state.json
                    │      ingest.py      │ ─── • Abort if marked "completed"
                    │   (State Engine)    │     • Extract start page checkpoint
                    └──────────┬──────────┘
                               │
                    Controlled Loop Execution (3.5s Delay)
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Gemini API      │ ◄── Generates 1,024-Dimension Arrays
                    │(gemini-embedding-001│
                    └──────────┬──────────┘
                               │
                               ├─► [429 Error: Per-Minute Limit] ──► Cooldown 65s, Retry Loop
                               ├─► [429 Error: Daily Quota Cap]  ──► Cache State, Exit Cleanly
                               │
                               ▼ (Successful Embedding Values)
                    ┌─────────────────────┐
                    │  Pinecone Database  │ ◄── Upserts vector arrays + metadata
                    └─────────────────────┘
```

---

### The State Mutation Lifecycle

The pipeline guarantees ingestion accuracy across continuous execution instances by persisting processing states to disk in `ingestion_state.json`. Each iteration checks, locks, and updates page-bound limits to prevent vector duplication and preserve rate limits.

Here is how the underlying state transitions as a single document scales through the compilation run:

```text
──────────────────────────────────────────────────────────────────────────────────────────────────
STAGE 01: FILE DISCOVERY & INITIALIZATION
──────────────────────────────────────────────────────────────────────────────────────────────────
 State Initial Configuration:
 {
     "The Art of War": {
         "last_processed_page": 0,
         "total_pages": 66,
         "status": "pending"
     }
 }
                                 │
                                 ▼
──────────────────────────────────────────────────────────────────────────────────────────────────
STAGE 02: PROCESSING BATCH COMPLETION
──────────────────────────────────────────────────────────────────────────────────────────────────
 State Mutated To:
 {
     "The Art of War": {
         "last_processed_page": 15,  ◄── [Locked checkpoint index post-Pinecone write]
         "total_pages": 66,
         "status": "pending"
     }
 }
                                 │
                                 ▼
──────────────────────────────────────────────────────────────────────────────────────────────────
STAGE 03: EMPTY LAYOUT / NON-EXTRACTABLE SLICE DEFLECTION
──────────────────────────────────────────────────────────────────────────────────────────────────
 State Mutated To:
 {
     "The Art of War": {
         "last_processed_page": 30,  ◄── [Advanced safely over unextractable image pages]
         "total_pages": 66,
         "status": "pending"         ◄── [Maintained pipeline loop active flag]
     }
 }
                                 │
                                 ▼
──────────────────────────────────────────────────────────────────────────────────────────────────
STAGE 04: PIPELINE CONVERGENCE & FINALIZATION
──────────────────────────────────────────────────────────────────────────────────────────────────
 State Mutated To:
 {
     "The Art of War": {
         "last_processed_page": 66,
         "total_pages": 66,
         "status": "completed"       ◄── [Pipeline flag sealed; local loops bypass file]
     }
 }
──────────────────────────────────────────────────────────────────────────────────────────────────
```

---

### Phase Breakdown

1. **Extraction & Sanitization Layer (`parser.py`):**

* **Action:** Opens the binary document, bounds the page processing constraints dynamically, cleans data fields, and builds structural text blocks.
* **Boundary Rule:** Restricts batch loops using an explicit lookahead strategy to prevent index range exceptions at document boundaries:

$$
\text{end\_page} = \min(\text{start\_page} + \text{max\_pages\_to\_process} - 1, \text{total\_pages})
$$

* **Sanitization:** Filters raw text using a strict regular expression to drop unprintable control characters and trailing layout noise while preserving word structure: `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]`.

2. **Stateful Batch Orchestration Engine (`ingest.py`):**

* **Action:** Regulates programmatic step cadence, structures token request arrays, maps Gemini exceptions, and routes arrays into Pinecone indices.
* **Defensive Controls:** Implements a mandatory `time.sleep(3.5)` throttling sequence before entering token generation phases. It also wraps network payloads inside an explicit `while not success:` backoff condition block to shield long jobs from transient network drops.

3. **Verification & Diagnostic Ledger (`continuous_sync_pipeline`):**

* **Action:** Performs comprehensive end-to-end multi-book testing by dispatching cross-examination evaluation queries directly to the operational production vector database cluster.
* **Metrics:** Evaluates query distance matches and returns confidence metrics alongside the source document fragments to verify indexing accuracy.

---

## 2. Functional Reference Registry

Every module inside `src/ingestion/` is designed as an isolated component for straightforward system updates. Use this matrix to adjust pipeline mechanics:

| Function Name                        | Code Location   | Primary Responsibility                                                                                          | Modification Levers (What to Edit)                                                                                                  |
| ------------------------------------ | --------------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `extract_and_chunk_pdf`            | `parser.py`   | Extracts raw strings from PDF segments, cleans non-printable ASCII noise, and chunks layouts.                   | Adjust`words_per_chunk` to vary semantic token density. Modify the cleaning RegEx to capture alternative encoding layouts.        |
| `run_parser_test`                  | `parser.py`   | Validates local extraction processing structures using standalone test assertions.                              | Update structural assertions to enforce strict word validation rules across different file types.                                   |
| `load_state` / `save_state`      | `ingest.py`   | Manages read/write serialization access to the JSON state ledger tracking matrix file.                          | Modify`STATE_FILE` path vectors or upgrade serialization types (e.g., migrating from JSON to a local SQLite engine).              |
| `upload_book_in_stateful_batches`  | `ingest.py`   | Orchestrates embedding requests, implements rate-limit safeguards, and manages Pinecone vector uploads.         | Tweak`pages_per_run` and `batch_size` settings. Alter `time.sleep()` constants to balance transmission rate configurations.   |
| `run_cross_examination_evaluation` | `ingest.py`   | Queries Pinecone with multi-source lookups to verify cross-book vector index accuracy.                          | Alter query strings inside`TEST_QUERIES`. Adjust lookahead depth limits (`top_k`) to check overall search recall.               |
| `continuous_sync_pipeline`         | `__init__.py` | Loops through all local files and runs the indexing pipeline until every reference text status reads completed. | Update the asset array definitions (`BOOK_PATHS`, `BOOKS`) or insert cross-book diagnostic strings into `CROSS_BOOK_QUERIES`. |

---

## 3. Subsystem Problem Ledger

This ledger lists identified bugs, logic issues, and performance challenges found during testing under free-tier API constraints, along with their solutions.

### Syntax & Structural Exceptions

* **Tuple Unpacking Discrepancies:** Refactoring the parser to return information pairs `(chunks_list, end_page)` caused structural breaks in scripts expecting a single list reference. Fixed by enforcing explicit destructuring: `chunks_list, _ = extract_and_chunk_pdf(...)`.
* **Iterable Unpacking ValueError:** Attempting to iterate directly over unzipped raw configuration sequences (`for path, name in (paths, names)`) caused runtime crashes. Resolved by using python's built-in `zip` function to combine configurations cleanly: `for path, name in zip(book_paths, books)`.
* **SDK Property Evolution Errors:** Legacy logic querying `.status_code` exceptions failed because the modern `google-genai` SDK nests exception status elements. Resolved by converting checks to use the native SDK string exception property `ce.code`.

### Algorithmic & Logical Skewing

* **Empty Page Slice Short-Circuits:** Encountering a sequence of blank or diagram-only pages generated an empty chunk array (`not chunks`). The original safety mechanism logged the change and returned a `True` completion value. This accidentally caused the outer loops to think the book was completely finished, skipping the remaining readable sections. Fixed by changing the handler to return `False` unless `end_page >= total_pages`, forcing the system to move forward to the next text slice.
* **Context Vector Starvation:** Standard vector searches occasionally retrieved repetitive keywords from a single source document. This filled the model's text window and squeezed out other helpful references. Fixed by expanding the retrieval pool to `top_k=8` and adding an explicit per-book metadata deduplication filter inside `nodes.py`.

### Program Scalability & API Constraints

* **Per-Minute Request Exhaustion (HTTP 429):** Rapid execution blocks regularly tripped over the strict 100 requests per minute limit. Resolved by combining proactive `time.sleep(3.5)` throttling delays with an exceptions handler that pauses execution for 65 seconds when a 429 occurs.
* **Daily Quota Exhaustion Tracking:** When the system hits its 1,000 requests per day limit, short-duration retry loops loop endlessly because the quota resets every 24 hours. Fixed by adding string inspections (`"day"` or `"perday"`) to the catch block. When matched, the system saves progress checkpoints and executes a clean shutdown (`exit(0)`).

---

## 4. Developer Onboarding & Subsystem Testing Guide

Follow this guide to initialize the isolated ingestion environment and run pipeline synchronization validations without deploying the full application interface.

### Phase 1: Environment Verification

Ensure the root configuration values are accurately set up inside your local `.env` file:

```bash
GEMINI_API_KEY="your_api_key_here"
PINECONE_API_KEY="your_pinecone_key_here"
PINECONE_INDEX_HOST="https://your-index-host-url.pinecone.io"
```

### Phase 2: Execution of Isolated Diagnostic Suite

Run individual validation commands from your terminal to verify that each stage of the ingestion pipeline works correctly:

```bash
# Step 1: Validate text extraction, cleanup regex patterns, and data framing structures
python -m src.ingestion.parser

# Step 2: Validate API connection, backoff recovery code, and Pinecone array storage operations
python -m src.ingestion.ingest

# Step 3: Run the entire system pipeline to discover and sync all local assets
python -m src.ingestion.__init__
```

### Expected Success Output Signatures

When running correctly, your console logs should look like this:

```text
=== RUNNING ISOLATED PARSER METRIC TEST ===
 -> Parsing pages 1 to 20 of 66 for 'The Art of War'...
 ✅ PARSER TEST PASSED. Sample Chunk Metadata: {'source': 'The Art of War', 'page': 1, 'text': '...'}

--- Checking sync engine status for: The Art of War ---
🚀 Resuming 'The Art of War' compilation from page 1/66...
 -> Parsing pages 1 to 15 of 66 for 'The Art of War'...
Generating vectors via Gemini API for 22 fragments...
 Pushing 22 records to Pinecone database cluster...
 Checkpoint locked: Saved progress up to page 15.

⚡ Database synchronization locked. Initiating cross-examination testing...
================================================================================
        🔴 DEEP ADVANCED CROSS-EXAMINATION LEDGER (TOP_3 CITATIONS)      
================================================================================
[Strategy Query 1]: "What are the five constant factors governing the military art?"
   ├─ Citation #1: The Art of War (Page 5) [Confidence: 0.8941]
   └─ Extract     : "The art of war, then, is governed by five constant factors..."
```

---

## 5. Architectural Evolution & Future-Proofing Options

The following features can be added to improve pipeline throughput as the system scales:

* **Asynchronous Request Concurrency:** Rebuilding processing loops to replace blocking `time.sleep` code with native `asyncio` execution patterns, paired with an asynchronous rate-limiting module like `aiolimiter`.
* **Dynamic Batch Resizing:** Implementing a sliding scale mechanism for batch sizes. If the engine intercepts consecutive 429 warnings, it scales down the `batch_size` parameter automatically, then scales it back up during stable connection windows.
* **Sliding Window Chunking:** Introducing overlapping token boundaries across consecutive text slices to preserve semantic context that would otherwise be split awkwardly across fixed-size chunks:

```text
 Chunk N:   [... Strategic layouts must maintain clear continuity with local assets ...]
 Overlap:                                       [clear continuity with]
 Chunk N+1:                                     [clear continuity with local assets and configurations ...]
```
