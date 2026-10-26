"""Document retrieval for RAG. Works offline with a tiny keyword retriever.
Optional Chroma embedding retrieval is enabled by running build_vectors.py.
"""
import re
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent / 'docs'
INDEX_DIR = Path(__file__).resolve().parent / 'data' / 'chroma'
STOPWORDS = {'the', 'is', 'a', 'an', 'i', 'my', 'your', 'to', 'for', 'can', 'we', 'of', 'do', 'what', 'how', 'after', 'with', 'our', 'about'}


def simple_search(question: str, count: int = 2):
    """Built-in backup retriever; no model downloads required."""
    terms = {word for word in re.findall(r'[a-z]+', question.lower()) if word not in STOPWORDS}
    # Simple synonyms make the tiny demo more useful. This is NOT semantic embeddings.
    if terms & {'return', 'money', 'damaged', 'refund', 'back'}:
        terms.add('refund')
    if terms & {'arrival', 'deliver', 'shipping', 'shipment', 'track'}:
        terms.add('shipping')
    if terms & {'guarantee', 'warranty', 'broken'}:
        terms.add('warranty')
    scored = []
    for path in sorted(DOCS_DIR.glob('*.txt')):
        content = path.read_text(encoding='utf-8')
        document_terms = set(re.findall(r'[a-z]+', (path.stem + ' ' + content).lower()))
        score = len(terms & document_terms)
        if score:
            scored.append((score, path.name, content))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [{'source': name, 'text': text} for _, name, text in scored[:count]]


def search_policies(question: str):
    """Use Chroma vectors if indexed, otherwise use small built-in text search."""
    if INDEX_DIR.exists():
        from langchain_chroma import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
        store = Chroma(collection_name='supportops', persist_directory=str(INDEX_DIR), embedding_function=embeddings)
        docs = store.similarity_search(question, k=2)
        return [{'source': doc.metadata.get('source', '?'), 'text': doc.page_content} for doc in docs]
    return simple_search(question)
