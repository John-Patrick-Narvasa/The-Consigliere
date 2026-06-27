# src/ingestion/parser.py
import re
import os
import fitz  # PyMuPDF

def extract_and_chunk_pdf(pdf_path: str, book_title: str, start_page: int = 1, max_pages_to_process: int = 20, words_per_chunk: int = 150) -> tuple[list[dict], int]:
    """
    Parses a segment of a PDF text layout page-by-page starting from start_page.
    Returns (chunks_list, last_processed_page).
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Missing resource layout: Could not find target path '{pdf_path}'")
        
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    chunks = []
    
    # Calculate the bounds of this batch execution
    end_page = min(start_page + max_pages_to_process - 1, total_pages)
    print(f" -> Parsing pages {start_page} to {end_page} of {total_pages} for '{book_title}'...")

    for page_idx in range(start_page - 1, end_page):
        page_num = page_idx + 1
        raw_text = doc.load_page(page_idx).get_text("text")
        
        if not raw_text or not raw_text.strip():
            continue
            
        cleaned_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', raw_text)
        words = cleaned_text.split()
        
        for i in range(0, len(words), words_per_chunk):
            chunk_text = " ".join(words[i:i + words_per_chunk])
            chunk_id = f"{book_title.lower().replace(' ', '_')}_p{page_num}_c{i}"
            
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    "source": book_title,
                    "page": page_num,
                    "text": chunk_text
                }
            })
            
    return chunks, end_page

def run_parser_test(pdf_path: str, book_title: str):
    """Isolated extraction tester metric"""
    print("\n=== RUNNING ISOLATED PARSER METRIC TEST ===")
    try:
        chunks = extract_and_chunk_pdf(pdf_path, book_title, words_per_chunk=150)
        assert len(chunks) > 0, "Parser test failed: No text fragments generated."
        print(f" ✅ PARSER TEST PASSED. Sample Chunk Metadata: {chunks[0]['metadata']}")
        return True
    except Exception as e:
        print(f" ❌ PARSER TEST FAILED: {str(e)}")
        return False