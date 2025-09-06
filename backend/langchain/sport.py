import numpy as np
import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from langchain.utils import model

# Загружаем модель (та же самая, что и для индексации)
# model = SentenceTransformer("all-MiniLM-L6-v2")


def load_data(vector_file="C:\\Users\\Admin\\Desktop\\Aidana\\SportBotAidana\\olammachatTS\\backend\\langchain\\vectors.npz", meta_file="C:\\Users\\Admin\\Desktop\\Aidana\\SportBotAidana\\olammachatTS\\backend\\langchain\\metadata.json"):
    # Загружаем эмбеддинги
    data = np.load(vector_file)
    embeddings = data["embeddings"]

    # Загружаем метаданные
    with open(meta_file, "r", encoding="cp1251") as f:
        metadata = json.load(f)

    return embeddings, metadata


def search(query, embeddings, metadata, top_k=3):
    # Получаем эмбеддинг вопроса
    query_embedding = model.encode([query])

    # Считаем косинусное сходство
    similarities = cosine_similarity(query_embedding, embeddings)[0]

    # Сортируем по убыванию
    top_indices = np.argsort(similarities)[::-1][:top_k]

    # Собираем результаты
    results = []
    for idx in top_indices:
        results.append({
            "id": metadata[idx]["id"],
            "text": metadata[idx]["text"],
            "score": float(similarities[idx])
        })

    return results


# if __name__ == "__main__":
#     # Загружаем данные
#     embeddings, metadata = load_data()

#     # Пример запроса
#     query = "что значит выиграл/проиграл концовок?"
#     results = search(query, embeddings, metadata, top_k=3)

#     print("🔎 Результаты поиска:")
#     for r in results:
#         print(f"[{r['score']:.3f}] {r['text']}")



