import os
import fitz  # PyMuPDF
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pinecone import Pinecone



load_dotenv()

# Initialize Clients
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
host_url = os.getenv("PINECONE_INDEX_HOST")
if not host_url:
    raise ValueError("ERROR: PINECONE_INDEX_HOST is missing or empty. Please check your .env file!")
index = pc.Index(host=host_url)

# Replace your current TEST_QUERIES array with this list to thoroughly audit accuracy
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
# =====================================================================
# ADDITION: HELPER VERIFICATION FUNCTION
# =====================================================================
def run_automated_evaluation(queries: list, index_client) -> None:
    """
    Loops through the 10 evaluation queries, hits the vector DB,
    and prints out a scannable ledger for manual accuracy verification.
    """
    print("\n" + "="*60)
    print("      CRITICAL RETRIEVAL ACCURACY REPORT OVER 10 QUERIES      ")
    print("="*60)
    
    for idx, query_text in enumerate(queries, start=1):
        # 1. Embed current testing query text
        res = ai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=query_text,
            config=types.EmbedContentConfig(output_dimensionality=1024)
        )
        vector = res.embeddings[0].values
        
        # 2. Extract match from Pinecone
        query_results = index_client.query(
            vector=vector,
            top_k=1,
            include_metadata=True
        )
        
        print(f"\n[Query {idx}/10]: \"{query_text}\"")
        if query_results.matches:
            match = query_results.matches[0]
            score = match.score
            page = match.metadata.get('page')
            source = match.metadata.get('source')
            text_snippet = match.metadata.get('text', '').replace('\n', ' ')
            
            # Print a scannable summary block
            print(f"  ├─► Verified Citation : {source} (Page {page}) [Confidence: {score:.4f}]")
            print(f"  └─► Text Context Snippet: \"{text_snippet[:140]}...\"")
        else:
            print("  └─► ❌ ERROR: Failed to fetch vector matching context criteria.")
            
    print("\n" + "="*60)
    print("   END OF LEDGER. PLEASE MANUALLY VERIFY RELEVANCY BEFORE PROCEEDING.   ")
    print("="*60)

def test_pipeline(pdf_path: str, book_title: str, test_queries: list):
    # =====================================================================
    # PROCESS 1: PARSING TEST
    # =====================================================================
    
    print("\n[Step 1] Testing PDF Parsing...")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"Successfully opened '{pdf_path}'. Total Pages: {total_pages}")

    # Sample page 10 for validation
    sample_page_num = min(10, total_pages)
    sample_page_text = doc.load_page(sample_page_num - 1).get_text("text").strip()
    print(f"-> Sample text extract from Page {sample_page_num} (First 150 chars):")
    print(f"   \"{sample_page_text[:150]}...\"")

    # =====================================================================
    # PROCESS 2: CHUNKING & METADATA BINDING
    # =====================================================================
    print("\n[Step 2] Testing Chunking & Metadata Enrichment...")
    chunks = []

    # For a high-fidelity test, let's process just the first 5 pages
    for page_idx in range(total_pages):
        page_num = page_idx + 1
        raw_text = doc.load_page(page_idx).get_text("text").strip()
        if not raw_text:
            continue
            
        cleaned_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', raw_text)

        # Basic chunking loop (words windowing)
        words = cleaned_text.split()
        words_per_chunk = 150
        for i in range(0, len(words), words_per_chunk):
            chunk_text = " ".join(words[i:i + words_per_chunk])
            
            chunk_id = f"{book_title.lower().replace(' ', '_')}_p{page_num}_c{i}"
            metadata = {
                "source": book_title,
                "page": page_num,
                "text": chunk_text  # Store the raw text inside metadata so it returns during searches!
            }
            chunks.append({"id": chunk_id, "text": chunk_text, "metadata": metadata})
            
    print(f"Created {len(chunks)} validation chunks from the first 5 pages.")
    print(f"-> Inspecting Chunk #0 Metadata: {chunks[0]['metadata']}")

    # =====================================================================
    # PROCESS 3: EMBEDDING GENERATION (Gemini models/models/models/text-embedding-004)
    # =====================================================================
    print("\n[Step 3] Testing Gemini Embedding Engine...")
    sample_text = chunks[0]['text']
    
    response = ai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=sample_text,
        config=types.EmbedContentConfig(output_dimensionality=1024)  # Matches your expected 1024
    )
    # Gemini models/models/text-embedding-004 returns a 1024-dimension vector
    vector_dimension = len(response.embeddings[0].values)
    print(f"Embedding successful! Vector Dimension match: {vector_dimension} (Expected: 1024)")

    # =====================================================================
    # PROCESS 4: PINECONE UPSERT
    # =====================================================================
    print("\n[Step 4] Upserting vectors to Pinecone...")
    import time


    upsert_data = []
    BATCH_SIZE = 50
    
    for i in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[i:i + BATCH_SIZE]
        batch_texts = [c['text'] for c in batch_chunks]
        
        print(f" -> Embedding batch {i // BATCH_SIZE + 1} ({len(batch_chunks)} chunks)...")
        
        try:
            res = ai_client.models.embed_content(
                model="gemini-embedding-001",
                contents=batch_texts, # Pass a list of texts here
                config=types.EmbedContentConfig(output_dimensionality=1024)
            )
            
            for idx, chunk in enumerate(batch_chunks):
                upsert_data.append({
                    "id": chunk['id'],
                    "values": res.embeddings[idx].values, # Extract the corresponding vector from list
                    "metadata": chunk['metadata']
                })
                
        except Exception as e:
            if "429" in str(e):
                print(" ⚠️ Rate limit hit. Cooling down for 16 seconds...")
                time.sleep(16)
                # Retry once after cooling down
                res = ai_client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=batch_texts,
                    config=types.EmbedContentConfig(output_dimensionality=1024)
                )
                for idx, chunk in enumerate(batch_chunks):
                    upsert_data.append({
                        "id": chunk['id'],
                        "values": res.embeddings[idx].values,
                        "metadata": chunk['metadata']
                    })
            else:
                raise e
        
        # Safe structural pause between distinct API calls to prevent tier spikes
        time.sleep(2.0)
        
    # Send vectors up to your online index
    upsert_response = index.upsert(vectors=upsert_data)
    print(f"Upsert Complete! Records added to cloud: {upsert_response.to_dict()}")

    # =====================================================================
    # PROCESS 5: END-TO-END RETRIEVAL TESTER
    # =====================================================================
    print("\n[Step 5] Triggering Live Retrieval Query Test...")
    run_automated_evaluation(test_queries, index)

if __name__ == "__main__":
    SAMPLE_FILE = "data/The_Art_Of_War.pdf" 
    test_pipeline(SAMPLE_FILE, "The Art of War", TEST_QUERIES)


# python src/ingestion/ingest_and_test.py