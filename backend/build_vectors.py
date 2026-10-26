"""Optional semantic RAG upgrade. Run once after installing requirements-rag.txt."""
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag import DOCS_DIR, INDEX_DIR


def main():
    documents = [Document(page_content=p.read_text(encoding='utf-8'), metadata={'source': p.name})
                 for p in sorted(DOCS_DIR.glob('*.txt'))]
    chunks = RecursiveCharacterTextSplitter(chunk_size=350, chunk_overlap=40).split_documents(documents)
    embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
    db = Chroma(collection_name='supportops', persist_directory=str(INDEX_DIR), embedding_function=embeddings)
    ids = [f"{doc.metadata['source']}-{i}" for i, doc in enumerate(chunks)]
    # Remove old documents so rebuilding doesn't keep stale chunks.
    try:
        old_ids = db.get()['ids']
        if old_ids:
            db.delete(ids=old_ids)
    except Exception:
        pass
    db.add_documents(chunks, ids=ids)
    print(f'Indexed {len(chunks)} chunks into Chroma:', INDEX_DIR)


if __name__ == '__main__':
    main()
