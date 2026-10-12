import numpy as np
import ollama

EMBED_MODEL = "nomic-embed-text"


def embed(text: str) -> np.ndarray:
    resp = ollama.embed(model=EMBED_MODEL, input=text)
    return np.array(resp["embeddings"][0])


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


v = embed("The Supplier shall provide the Services with reasonable skill and care.")
print("dimensions:", v.shape[0])
print("first 5 values:", v[:5].round(4))
print("vector length (norm):", round(float(np.linalg.norm(v)), 3))

query = "How long do I have to pay an invoice?"
docs = [
    "Undisputed invoices shall be paid within forty-five (45) days of receipt of a valid invoice.",
    "Interest on late payment accrues at 4% per annum above the Bank of England base rate.",
    "This Agreement is governed by the laws of England and Wales.",
]
q = embed(query)
for d in docs:
    print(f"{cosine(q, embed(d)):.3f}  {d[:63]}...")
