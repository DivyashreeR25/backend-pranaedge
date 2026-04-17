import requests
import numpy as np
import os

HF_TOKEN = os.getenv("HF_TOKEN")

API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

headers = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

# 🔹 Get embedding from HuggingFace API
def get_embedding(text):
    response = requests.post(
        API_URL,
        headers=headers,
        json={"inputs": text}
    )
    return response.json()[0]


# 🔹 Precompute embeddings once
DOCUMENTS = [item["content"] for item in KNOWLEDGE_BASE]
DOC_EMBEDDINGS = [get_embedding(doc) for doc in DOCUMENTS]


# 🔹 Cosine similarity
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# 🔹 Retrieve relevant context
def retrieve_ayurveda_context(query: str, k: int = 3) -> str:
    query_embedding = get_embedding(query)

    scores = [
        cosine_similarity(query_embedding, emb)
        for emb in DOC_EMBEDDINGS
    ]

    top_indices = np.argsort(scores)[-k:][::-1]

    context = "\n\n".join([DOCUMENTS[i] for i in top_indices])
    return context
