from pathlib import Path
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions

def ingest_faq_data(path: Path):
    """Loads CSV data and saves it to a persistent Chroma database."""
    print("Initializing Chroma client for ingestion...")
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection_name_faq = "faqs"
    
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    collection = chroma_client.get_or_create_collection(
        name=collection_name_faq,
        embedding_function=ef
    )
    
    # Check if data is already there so we don't duplicate it
    if collection.count() > 0:
        print("FAQ database already contains data. Skipping ingestion.")
        return
        
    print(f"Reading CSV from: {path}")
    if not path.exists():
        print(f"Error: Could not find CSV file at {path}")
        return

    # Read and parse the CSV
    df = pd.read_csv(path)
    docs = df["question"].tolist()
    answers = df["answer"].tolist()
    metadata = [{"answer": a} for a in answers]
    ids = [f"id_{i}" for i in range(len(docs))]
    
    # Inject into ChromaDB
    collection.add(
        documents=docs,
        metadatas=metadata,
        ids=ids
    )
    print("FAQ database ingestion completed successfully!")

if __name__ == "__main__":
    # Locate the CSV file inside your resources folder
    faq_path = Path(__file__).parent / "resources" / "faq_data.csv"
    ingest_faq_data(faq_path)
