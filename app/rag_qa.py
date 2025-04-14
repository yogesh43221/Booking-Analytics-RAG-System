# app/rag_qa.py

import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
import requests
import json
import os
import pickle

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2'
FAISS_INDEX_PATH = 'vector_store/faiss_index.index'
DOCS_PATH = 'vector_store/text_data.pkl'
OLLAMA_API_URL = 'http://localhost:11434/api/generate'
LLM_MODEL_NAME = 'mistral'
TOP_K_RESULTS = 3

# --- Global Variables (Load resources once) ---
try:
    print("Loading FAISS index...")
    if not os.path.exists(FAISS_INDEX_PATH):
        raise FileNotFoundError(f"FAISS index file not found at {FAISS_INDEX_PATH}. Please run create_vector_store.py first.")
    index = faiss.read_index(FAISS_INDEX_PATH)
    print(f"✅ FAISS index loaded successfully. Contains {index.ntotal} vectors.")

    print(f"Loading sentence transformer model: {MODEL_NAME}...")
    embedding_model = SentenceTransformer(MODEL_NAME)
    print("✅ Embedding model loaded successfully.")

    # Load precomputed summaries
    print("Loading context summaries from text_data.pkl...")
    if not os.path.exists(DOCS_PATH):
        raise FileNotFoundError(f"text_data.pkl not found at {DOCS_PATH}. Please re-run create_vector_store.py.")
    with open(DOCS_PATH, 'rb') as f:
        all_formatted_texts = pickle.load(f)
    print(f"✅ Loaded {len(all_formatted_texts)} summaries.")

except Exception as e:
    print(f"❌ Error loading resources: {e}")
    index = None
    embedding_model = None
    all_formatted_texts = []

# --- Core RAG Functions ---

def get_relevant_context(query: str, k: int = TOP_K_RESULTS):
    if index is None or embedding_model is None or not all_formatted_texts:
        print("❌ RAG resources not loaded properly.")
        return []

    try:
        print(f"Embedding query: '{query}'")
        query_embedding = embedding_model.encode([query], convert_to_numpy=True).astype('float32')
        print(f"Searching FAISS index for top {k} results...")
        distances, indices = index.search(query_embedding, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(all_formatted_texts):
                results.append({"summary": all_formatted_texts[idx], "score": float(dist)})

        print(f"Retrieved {len(results)} relevant texts.")
        return results
    except Exception as e:
        print(f"❌ Error during context retrieval: {e}")
        return []

def generate_response_ollama(prompt: str):
    """Sends prompt to Ollama API and gets response."""
    print("Sending prompt to Ollama...")
    payload = {
        "model": LLM_MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()

        response_data = response.json()
        answer = response_data.get("response", "").strip()
        print("✅ Received response from Ollama.")
        return answer
    except requests.exceptions.RequestException as e:
        print(f"❌ Error communicating with Ollama API: {e}")
        if "Connection refused" in str(e):
            print("⚠️ Make sure the Ollama server is running.")
        return "Sorry, I encountered an error trying to connect to the language model."
    except json.JSONDecodeError:
        print(f"❌ Error decoding JSON response from Ollama: {response.text}")
        return "Sorry, I received an invalid response from the language model."
    except Exception as e:
        print(f"❌ An unexpected error occurred during LLM generation: {e}")
        return "Sorry, an unexpected error occurred while generating the response."

def format_prompt(query: str, context: list[dict]) -> str:
    if not context:
        context_str = "No relevant context found."
    else:
        context_str = "\n---\n".join([c["summary"] for c in context])

    prompt = f"""
Based on the following context about hotel bookings, please answer the user's question.
If the context does not provide the answer, say you don't have enough information.

Context:
---
{context_str}
---

Question: {query}

Answer:
"""
    print("Formatted prompt for LLM.")
    return prompt

# --- Main Orchestration Function ---

def answer_question(query: str) -> dict:
    print(f"\n--- Processing query: '{query}' ---")
    relevant_texts = get_relevant_context(query)
    prompt_for_llm = format_prompt(query, relevant_texts)
    answer = generate_response_ollama(prompt_for_llm)

    # Extract only the summary strings for the API response
    context_summaries = [ctx["summary"] for ctx in relevant_texts] if relevant_texts else []
    return {
        "query": query,
        "answer": answer,
        "retrieved_context": context_summaries # Match the Answer model in main.py
        # You can still log the full relevant_texts with scores internally if needed
    }

# --- Example Usage ---
if __name__ == '__main__':
    if index and embedding_model and all_formatted_texts:
        test_queries = [
            "Which locations had the most cancellations?",
            "What was the average lead time for bookings in Portugal (PRT)?",
            "Tell me about bookings arriving in July 2017."
        ]

        for q in test_queries:
            result = answer_question(q)
            print(f"\nResult for: {q}")
            print(json.dumps(result, indent=2))
    else:
        print("❌ Cannot run examples because resources failed to load.")
