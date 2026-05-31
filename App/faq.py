

import pandas as pd
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from groq import Groq
from dotenv import load_dotenv
import os
import difflib

# Load the .env file located next to this module
load_dotenv(dotenv_path=Path(__file__).parent / '.env')

# ✅ Persistent DB (IMPORTANT FIX)
try:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
except Exception:
    chroma_client = None

collection_name_faq = "faqs"

groq_client = Groq()

# Try to initialise a sentence-transformers embedding function; fall back gracefully if torch/transformers unavailable
ef = None
_EMBEDDING_AVAILABLE = True
try:
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
except Exception as e:
    _EMBEDDING_AVAILABLE = False
    ef = None

# -----------------------------
# INGESTION
# -----------------------------
def ingest_faq_data(path: Path):
    # If chroma or embeddings are not available, skip vector ingestion
    if chroma_client is None or not _EMBEDDING_AVAILABLE:
        print("Chroma or sentence-transformers not available — skipping vector ingestion.")
        return

    collection = chroma_client.get_or_create_collection(
        name=collection_name_faq,
        embedding_function=ef
    )

    # Prevent duplicate ingestion
    if collection.count() > 0:
        print("FAQ already ingested. Skipping...")
        return

    print("Ingesting FAQ data into Chroma...")

    df = pd.read_csv(path)

    docs = df["question"].tolist()
    answers = df["answer"].tolist()

    metadata = [{"answer": a} for a in answers]
    ids = [f"id_{i}" for i in range(len(docs))]

    collection.add(
        documents=docs,
        metadatas=metadata,
        ids=ids
    )

    print("FAQ ingestion completed successfully")

# -----------------------------
# RETRIEVAL
# -----------------------------
def get_relevant_qa(query: str):
    # Prefer vector search when available
    if chroma_client is not None and _EMBEDDING_AVAILABLE:
        collection = chroma_client.get_collection(name=collection_name_faq)
        return collection.query(
            query_texts=[query],
            n_results=2
        )

    # Fallback: simple fuzzy text search over the CSV file
    faq_path = Path(__file__).parent / "resources" / "faq_data.csv"
    df = pd.read_csv(faq_path)
    questions = df["question"].tolist()
    answers = df["answer"].tolist()

    # Use difflib to find closest matches
    matches = difflib.get_close_matches(query, questions, n=2, cutoff=0.1)

    # Build result structure similar to chroma's query response
    metadatas = []
    for m in matches:
        idx = questions.index(m)
        metadatas.append({"answer": answers[idx]})

    # If no close matches, return the top 2 by simple substring scoring
    if not metadatas:
        scores = [(i, query.lower() in q.lower()) for i, q in enumerate(questions)]
        ranked = [i for i, has in scores if has]
        for i in ranked[:2]:
            metadatas.append({"answer": answers[i]})

    # Ensure we always return two items (pad with empty answers)
    while len(metadatas) < 2:
        metadatas.append({"answer": ""})

    return {"metadatas": [metadatas]}

# -----------------------------
# RAG CHAIN
# -----------------------------
def faq_chain(query: str):

    result = get_relevant_qa(query)

    # ✅ FIX: clean + readable context
    context = "\n".join(
        [m.get("answer", "") for m in result["metadatas"][0]]
    )

    return generate_answer(query, context)

# -----------------------------
# LLM CALL
# -----------------------------
def generate_answer(query: str, context: str):

    prompt = f"""
You are an FAQ assistant.

Answer ONLY using the context below.
If answer is not in context, say "I don't know".

QUESTION:
{query}

CONTEXT:
{context}
"""

    # Prefer configured model in App/.env; fall back to a supported default
    model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=model_name
    )
    try:
        return response.choices[0].message.content
    except Exception as e:
        return f"Sorry, I couldn't generate an answer right now ({type(e).__name__})."


# -----------------------------
# TEST RUN
# -----------------------------
if __name__ == "__main__":

    faq_path = Path(__file__).parent / "resources" / "faq_data.csv"

    ingest_faq_data(faq_path)

    query = "Do you take cash as payment option?"

    answer = faq_chain(query)

    print("Query:", query)
    print("Answer:", answer)