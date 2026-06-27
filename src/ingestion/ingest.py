# src/ingestion/ingest.py
import os
import time
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError 
from pinecone import Pinecone

from .parser import extract_and_chunk_pdf

load_dotenv()

ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_HOST = os.getenv("PINECONE_INDEX_HOST")
index = pc.Index(host=INDEX_HOST)

STATE_FILE = "src/ingestion/ingestion_state.json"

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def upload_book_in_stateful_batches(pdf_path: str, book_title: str, pages_per_run: int = 15, batch_size: int = 20):
    """Processes a book in micro-batches of pages, recording state to resume safely."""
    state = load_state()
    
    # Initialize state structure for a brand new book
    if book_title not in state:
        import fitz
        doc = fitz.open(pdf_path)
        state[book_title] = {
            "last_processed_page": 0,
            "total_pages": len(doc),
            "status": "pending"
        }
        save_state(state)

    book_state = state[book_title]
    
    if book_state["status"] == "completed":
        print(f" 💾 NOTICE: '{book_title}' marked completed locally. Skipping pipeline execution.")
        return True

    start_page = book_state["last_processed_page"] + 1
    total_pages = book_state["total_pages"]

    if start_page > total_pages:
        book_state["status"] = "completed"
        save_state(state)
        return True

    print(f"\n🚀 Resuming '{book_title}' compilation from page {start_page}/{total_pages}...")
    
    # Extract structural records for just this slice of pages
    chunks, end_page = extract_and_chunk_pdf(
        pdf_path, book_title, start_page=start_page, max_pages_to_process=pages_per_run
    )

    if not chunks:
        print(" ⚠️ Empty slice encountered. Updating state matrix to next checkpoint.")
        book_state["last_processed_page"] = end_page
        if end_page >= total_pages: book_state["status"] = "completed"
        save_state(state)
        return True

    upsert_payload = []
    print(f"Generating vectors via Gemini API for {len(chunks)} fragments...")
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_texts = [c['text'] for c in batch]

        time.sleep(3.5)

        # FIX: Robust adaptive while loop for clean retry handling
        success = False
        while not success:
            try:
                res = ai_client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=batch_texts,
                    config=types.EmbedContentConfig(output_dimensionality=1024)
                )
                for idx, chunk in enumerate(batch):
                    upsert_payload.append({
                        "id": chunk['id'],
                        "values": res.embeddings[idx].values,
                        "metadata": chunk['metadata']
                    })
                success = True # Breaks the loop on success
            except ClientError as ce:
                if ce.code == 429:
                    # FIX: Safely parse the entire exception string to catch deep dict keys
                    full_error_string = str(ce).lower()
                    
                    if "day" in full_error_string or "perday" in full_error_string:
                        print("\n🛑 DAILY CAP DETECTED: You have officially exhausted Gemini's 1,000 free daily requests.")
                        print(f"💾 Checkpoint safely preserved at page {book_state['last_processed_page']}. Exiting gracefully...")
                        exit(0)
                        
                    print(" ⚠️ Per-Minute Limit reached. Cooling down for 65 seconds...")
                    time.sleep(65)
                else:
                    raise ce
            except Exception as e:
                raise e

    if upsert_payload:
        print(f" Pushing {len(upsert_payload)} records to Pinecone database cluster...")
        index.upsert(vectors=upsert_payload)

    # Persist the current snapshot of successful work
    book_state["last_processed_page"] = end_page
    if end_page >= total_pages:
        book_state["status"] = "completed"
        print(f" 🎉 SUCCESS: Ingestion pipeline finalized fully for '{book_title}'!")
    else:
        print(f" Checkpoint locked: Saved progress up to page {end_page}.")
        
    save_state(state)
    return False

def run_cross_examination_evaluation(queries: list, top_k: int = 3) -> None:
    """Queries Pinecone globally with top_k > 1 to pull multiple pages and cross-reference books."""
    print("\n" + "="*80)
    print(f"        🔴 DEEP ADVANCED CROSS-EXAMINATION LEDGER (TOP_{top_k} CITATIONS)        ")
    print("="*80)
    
    for idx, query_text in enumerate(queries, start=1):
        res = ai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=query_text,
            config=types.EmbedContentConfig(output_dimensionality=1024)
        )
        vector = res.embeddings[0].values
        
        query_results = index.query(vector=vector, top_k=top_k, include_metadata=True)
        
        print(f"\n[Strategy Query {idx}]: \"{query_text}\"")
        if query_results.matches:
            for match_idx, match in enumerate(query_results.matches, start=1):
                source = match.metadata.get('source', 'Unknown Document')
                page = int(match.metadata.get('page', 0))
                score = match.score
                extract = match.metadata.get('text', '')[:110].strip().replace('\n', ' ')
                
                print(f"   ├─ Citation #{match_idx}: {source} (Page {page}) [Confidence: {score:.4f}]")
                print(f"   └─ Extract     : \"{extract}...\"")
        else:
            print("   └─ ❌ Vector mapping yielded zero results.")
    print("\n" + "="*80)

if __name__ == "__main__":
    TEST_QUERIES = [
    # Chapter I: Laying Plans
    "What are the five constant factors governing the military art?",
    # Chapter II: Waging War
    "What fraction of public revenue is dissipated on broken chariots and wagons?",
    # Chapter III: Attack by Stratagem
    "Why does supreme excellence consist of breaking the enemy's resistance without fighting?",
    # Chapter IV: Tactical Dispositions
    "Name the five elements of military method starting with Measurement.",
    # Chapter V: Energy
    "What are the five primary colors and five cardinal tastes used to illustrate?",
    # Chapter VI: Weak Points and Strong
    "Why are military tactics compared directly to the natural course of water?",
    # Chapter VII: Maneuvering
    "What is the physical danger of marching a hundred LI or fifty LI to wrest an advantage?",
    # Chapter VIII: Variation in Tactics
    "What are the five dangerous faults or besetting sins that can affect a general?",
    # Chapter IX: The Army on the March
    "What are the signs indicated by a high column of dust versus a low wide spread of dust?",
    # Chapter X: Terrain
    "Name the six distinct kinds of terrain beginning with accessible and entangling ground.",
    # Chapter XI: The Nine Situations
    "How does the coordination of a skillful army resemble the Shuai-jan snake of the Ch'ang mountains?",
    # Chapter XII: The Attack by Fire
    "What are the five ways of attacking with fire and what are the proper environmental conditions?",
    # Chapter XIII: The Use of Spies
    "What are the five classes of spies starting with local and inward spies?"
    ]
    
    # 1. First execution - Run isolated module integration test
    run_parser_test("data/The_Art_Of_War.pdf", "The Art of War")
    
    # 2. Run the main processing workflow (skips automatically if data is already uploaded)
    upload_book_to_vector_store("data/The_Art_Of_War.pdf", "The Art of War")
    
    # 3. Fire audit checks against the live vector database
    run_automated_evaluation(TEST_QUERIES)