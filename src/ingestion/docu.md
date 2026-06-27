
# Ingestion Subsystem Technical Documentation

This document provides a technical overview of the stateful document ingestion engine built inside **The Consigliere** project workspace. The subsystem processes text assets, splits them into structured pieces, transforms them into high-dimensional vector representations via the Gemini API, and updates a centralized Pinecone vector database cluster.

---

## 1. Overall System Architecture & Data Flow

The ingestion framework utilizes an incremental, batch-driven data pipeline designed to prevent data duplication and protect against network errors or external API rate limits.

```
       [ Local PDF Files ]
               │
               ▼
   ┌───────────────────────┐
   │    parser.py          │ <── Reads page slice (e.g., 15 pages)
   │    (PyMuPDF / re)     │
   └───────────┬───────────┘
               │ Outputs text chunks
               ▼
   ┌───────────────────────┐       Checks ingestion_state.json
   │    ingest.py          │ ─────  • Skip if "completed"
   │    (State Engine)     │        • Resume from last valid page
   └───────────┬───────────┘
               │
      Paced Loop (3.5s Delay)
               │
               ▼
   ┌───────────────────────┐
   │    Gemini API         │ <── Generates 1024-Dimension Vectors
   │  (Embedding Model)    │
   └───────────┬───────────┘
               │ 
               ├─ [429 Error: Per-Minute Limit] ──> Sleeps 65 seconds, Retries
               ├─ [429 Error: Daily Cap Limit]  ──> Saves State, Exits Cleanly
               │
               ▼ (Successful Embeddings)
   ┌───────────────────────┐
   │   Pinecone Database   │ <── Upserts vectors with explicit metadata
   └───────────────────────┘
```

### End-to-End Execution Lifecyle

1. **Pipeline Execution:** The entry point reads project configurations and initializes processing parameters (`pages_per_run=15`, `batch_size=20`).
2. **Local State Check:** The program scans `ingestion_state.json` to verify if the file has been processed or determines the precise restart index.
3. **Chunking Process:** The parser opens the target PDF, extracts raw text strings from the specified range, cleans non-printable ASCII characters, and builds metadata payloads.
4. **Vector Generation with Backoff Loops:** The text blocks are batched and dispatched to the `gemini-embedding-001` engine. An adaptive exception loop intercepts rate limits and coordinates retry logic.
5. **Database Sync & State Save:** High-dimensional arrays are written directly to Pinecone. The state tracker locks down the progress snapshot on disk, allowing the application to safely exit or queue subsequent books.

---

## 2. Module Specifications & Method Details

### `src/ingestion/parser.py`

#### `extract_and_chunk_pdf(...)`

Processes a local PDF asset in page-bounded intervals, cleaning data and assembling the chunk payloads.

* **Signature:** `extract_and_chunk_pdf(pdf_path: str, book_title: str, start_page: int = 1, max_pages_to_process: int = 20, words_per_chunk: int = 150) -> tuple[list[dict], int]`
* **Internal Mechanics:**

1. Bounds calculation restricts extraction to the maximum available pages:

$$
\text{end\_page} = \min(\text{start\_page} + \text{max\_pages\_to\_process} - 1, \text{total\_pages})
$$

2. PyMuPDF extracts raw strings through `.get_text("text")`. Empty layout pages are caught and skipped.
3. Regular expressions filter out noisy control characters: `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]`.
4. Text strings are split into arrays by whitespace and packed into blocks matching the `words_per_chunk` parameter.
5. Builds a uniquely identifiable record footprint containing source properties and line context.

```
Raw Page Text  ───> [ Clean RegEx Filter ] ───> [ Token Splitter ] ───> Fixed Sub-Segments
                                                                          (150 Words Each)
                                                                                 │
   ┌─────────────────────────────────────────────────────────────────────────────┘
   ▼
Constructed Record Payload:
 {
   "id": "the_art_of_war_p12_c0",
   "text": "Regulated tactical actions dictate...",
   "metadata": { "source": "The Art of War", "page": 12, "text": "..." }
 }
```

---

### `src/ingestion/ingest.py`

#### `load_state()` / `save_state(state)`

Handles read and write access to the tracking matrix file `ingestion_state.json`.

```json
{
    "The Art of War": {
        "last_processed_page": 66,
        "total_pages": 66,
        "status": "completed"
    },
    "Building a Second Brain": {
        "last_processed_page": 165,
        "total_pages": 237,
        "status": "pending"
    }
}
```

#### `upload_book_in_stateful_batches(...)`

Manages the orchestration loop, rate control safeguards, error mapping, and upsert distribution.

* **Signature:** `upload_book_in_stateful_batches(pdf_path: str, book_title: str, pages_per_run: int = 15, batch_size: int = 20)`
* **Internal Mechanics:**
* Verifies completion metrics. If the document state evaluates to `"completed"`, execution halts immediately.
* Slices matching segments, calling `extract_and_chunk_pdf` using `last_processed_page + 1`.
* Iterates through sub-arrays using the configured `batch_size`.
* Implements a standard `time.sleep(3.5)` step before every API request to regulate structural throughput under rate limits.
* Encapsulates vector creation inside a `while not success:` conditional branch to sustain long-running ingestion jobs across transient network drops.

#### `run_cross_examination_evaluation(...)`

Executes validation checks against the live index to verify retrieval performance across all compiled reference texts.

```
       [ Input User Query ]
                │
                ▼
      [ Gemini API Embed ] ───> 1024-Dimension Float Array
                                        │
                                        ▼
                           [ Pinecone Index Query ]
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼ (Match 1)                                           ▼ (Match 2)
  Source: "The Art of War"                              Source: "Second Brain"
  Page: 34 | Score: 0.8912                              Page: 112 | Score: 0.7421
```

---

## 3. Production Failure Modes & Resolution Ledger

The ingestion subsystem contains custom error handling designed to resolve several edge cases encountered during development under the free-tier API constraints:

| Error Vector / Crash State           | Structural Root Cause | Implemented Resolution Strategy |
| ------------------------------------ | --------------------- | ------------------------------- |
| **HTTP 429: Per-Minute Limit** |                       |                                 |

`RESOURCE_EXHAUSTED` | Intermittent traffic bursts exceeded the **100 Requests Per Minute (RPM)** API ceiling. | Intercepts `ClientError` where `ce.code == 429`. Suspends processing execution for **65 seconds** to clear the rolling server window before automatically retrying. |
| **AttributeError**

`'ClientError' has no attribute 'status_code'` | Version updates in the modern native `google-genai` SDK moved the standard error integer into a nested property. | Refactored validation blocks away from the legacy `.status_code` designation to map directly to the native SDK exception property: `ce.code`. |
| **Infinite Recovery Loops**

`Suspending loop for 65 seconds...` | Once the API key hits its **1,000 Requests Per Day** quota, standard short-duration sleep periods fail repeatedly because the limit lasts for 24 hours. | Upgraded error checking to capture the full string dump via `str(ce).lower()`. If `"day"` or `"perday"` matches, it prints a clear notification, updates your progress file, and runs a clean system exit (`exit(0)`). |

---

## 4. Testing & Verification Protocol

### Running Isolated Unit Checks

Before spinning up the complete pipeline, verify your document extraction system using the built-in parser entry point:

```bash
# Execute isolated engine tests directly inside your virtual environment
python -m src.ingestion.parser
```

### Step-by-Step Validation Guide

1. **Verify Vector Formats:** Confirm that your text preprocessing is splitting documents correctly without breaking paragraphs or losing words.

* Run the isolated parser test and inspect the terminal output.
* Verify that your text chunk dictionaries generate consistent identifiers like `book_title_p12_c0` and check that the metadata payload includes the full raw text snippet.

2. **Verify Resumption Behavior:** Test that the system handles interruptions properly by terminating the script mid-run.

* Run the ingestion pipeline command: `python -m src.ingestion.__init__`
* Let the engine process a few page blocks, then terminate it early using `Ctrl + C`.
* Open `src/ingestion/ingestion_state.json` and ensure `last_processed_page` matches the last successful log entry.
* Re-run the pipeline command. The engine should immediately skip completed sections and resume on the next unprocessed page range.

3. **Verify Database Consistency:** Ensure that your data uploads are completing successfully and matching cleanly against user queries.

* Wait for a successful batch upload notification, then review your Pinecone web console.
* Confirm that your vector dimensions match the expected configuration (1,024 vector dimensions).
* Run your evaluation script to send test queries to the index, and verify that the context matches your source documents.

---

## 5. Areas for Improvement

While the current architecture safely protects data ingestion across long-running jobs, several optimizations can be introduced as the project grows:

* **Asynchronous Request Concurrency:** Transition processing loops away from blocking `time.sleep()` schedules over to native `asyncio` execution combined with an asynchronous rate-limiter component like `aiolimiter`.
* **Dynamic Batch Resizing:** Implement a sliding scale for batch sizes. If the system encounters multiple 429 errors, it can automatically scale down the `batch_size` parameter dynamically before climbing back up during stable periods.
* **Sliding Window Chunking:** Introduce an overlapping token window configuration to prevent semantic context from being split awkwardly across consecutive chunks:

```
  Chunk N:     [... Strategic layouts must maintain clear continuity with local assets ...]
  Overlap:                                            [clear continuity]
  Chunk N+1:                                         [clear continuity with local assets and configurations ...]
```
