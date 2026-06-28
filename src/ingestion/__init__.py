# src/ingestion/__init__.py
import os
from .ingest import upload_book_in_stateful_batches, run_cross_examination_evaluation, load_state

BOOK_PATHS = [
    "data/The_Art_Of_War.pdf", 
    "data/Building a Second Brain By Tiago Forte-pdfread.net.pdf", 
    "data/Ego is the Enenmy ( PDFDrive ).pdf", 
    "data/Robert Greene, Joost Elffers - The 48 laws of power-Profile Books (2000).pdf", 
    "data/The Holy Bible (KJV).pdf",
    "data/Atomic Habits by James Clear.pdf.pdf"
]
BOOKS = ["The Art of War", 
         "Building a Second Brain", 
         "Ego is the Enemy", 
         "The 48 laws of power", 
         "The Holy Bible (KJV)", 
         "Atomic Habits"
]

CROSS_BOOK_QUERIES = [
    "Give me strategies combining the deceptive arts of war with managing a person's pride and public presence.",
    "What links historical laws of power with a tactical strategy for military defense?",
    "How do the concepts of structuring organization systems relate to biblical principles of management?"
]

def continuous_sync_pipeline(book_paths: list[str], books: list[str]):
    """Loops through all files and indexes them in digestible slices until fully completed."""
    for path, name in zip(book_paths, books):
        if not os.path.exists(path):
            print(f" ❌ Skipping: Resource path error on '{path}'")
            continue
            
        print(f"\n--- Checking sync engine status for: {name} ---")
        
        # Keep processing the same book in safe page increments until finished
        is_done = False
        while not is_done:
            # processes 15 pages at a time, batching text inside at 20 strings per api request
            is_done = upload_book_in_stateful_batches(path, name, pages_per_run=15, batch_size=20)
            
    print("\n⚡ Database synchronization locked. Initiating cross-examination testing...")
    run_cross_examination_evaluation(CROSS_BOOK_QUERIES, top_k=3)

if __name__ == "__main__":
    continuous_sync_pipeline(BOOK_PATHS, BOOKS)
    
# if __name__ == "__main__":
#     # # test single book
#     # extract_and_chunk_pdf("data/The_Art_Of_War.pdf", "The Art of War")
#     # run_parser_test("data/The_Art_Of_War.pdf", "The Art of War")
#     # upload_book_to_vector_store("data/The_Art_Of_War.pdf", "The Art of War")
#     # is_book_already_indexed("The Art of War")
#     # run_automated_evaluation("The Art of War")

#     # test multiple books
#     add_books(BOOK_PATHS, BOOKS)
