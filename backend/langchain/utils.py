from sentence_transformers import SentenceTransformer
import numpy as np
import json


def save_emb(chunks, embeddings, filename = "vectors.npz", meta_file= "metadata.json"):
    np.savez(filename, embeddings = embeddings)
    metadata = []
    for i, chunk in enumerate(chunks):
        metadata.append({
            "id": i,
            "text": chunk
        })

    with open(meta_file, "w", encoding="cp1251") as f:
        json.dump(metadata, f, ensure_ascii=False, indent =2)
    print(f"Сохранено {len(chunks)} в файл {filename} и {meta_file}")



model = SentenceTransformer("all-MiniLM-L6-v2")

def embedding(path: str):
    with open(path, "r", encoding = "cp1251") as f:
        text = f.read()
    chunks = split(text, chunk_size=50, overlap=10)
    embeddings = model.encode(chunks)
    print("Колво эмбеддинов: ", len(embeddings))
    print("Размерность: ", len(embeddings[0]))
    return chunks, embeddings
    

def split(text, chunk_size = 50, overlap = 10):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# if __name__ == "__main__":
#     chunks, embeddings = embedding("типа.txt")
#     save_emb(chunks, embeddings)