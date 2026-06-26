import fitz  # PyMuPDF
from langchain_core.documents import Document

def parse_and_chunk_pdf(pdf_path: str, book_title: str, chunk_size: int = 1000) -> list[Document]:
    doc = fitz.open(pdf_path)
    documents = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text").strip()
        
        if not text:
            continue
            
        # Simple sliding window chunking per page to guarantee exact page metadata
        # For small chunks, you can split text by paragraphs or word counts
        words = text.split()
        for i in range(0, len(words), chunk_size // 5):  # Rough word-count approximation
            chunk_text = " ".join(words[i:i + chunk_size])
            
            # Encapsulate into LangChain's standard Document format
            metadata = {
                "source": book_title,
                "page": page_num + 1  # 1-indexed for reader readability
            }
            documents.append(Document(page_content=chunk_text, metadata=metadata))
            
    return documents