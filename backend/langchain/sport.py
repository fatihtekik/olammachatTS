import numpy as np
import json
import os
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from langchain.utils import model

# Загружаем модель (та же самая, что и для индексации)
# model = SentenceTransformer("all-MiniLM-L6-v2")

# Получаем абсолютный путь к текущей директории
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VECTOR_FILE = os.path.join(CURRENT_DIR, "vectors.npz")
DEFAULT_META_FILE = os.path.join(CURRENT_DIR, "metadata.json")


def load_data(vector_file=None, meta_file=None):
    """
    Загружает эмбеддинги и метаданные для RAG
    
    Args:
        vector_file: Путь к файлу с векторами (по умолчанию vectors.npz в текущей папке)
        meta_file: Путь к файлу с метаданными (по умолчанию metadata.json в текущей папке)
    
    Returns:
        embeddings: numpy array с векторами
        metadata: list с метаданными
    """
    # Используем пути по умолчанию если не указаны
    if vector_file is None:
        vector_file = DEFAULT_VECTOR_FILE
    if meta_file is None:
        meta_file = DEFAULT_META_FILE
    
    # Проверяем существование файлов
    if not os.path.exists(vector_file):
        print(f"❌ Файл с векторами не найден: {vector_file}")
        raise FileNotFoundError(f"Файл с векторами не найден: {vector_file}")
    
    if not os.path.exists(meta_file):
        print(f"❌ Файл с метаданными не найден: {meta_file}")
        raise FileNotFoundError(f"Файл с метаданными не найден: {meta_file}")
    
    print(f"✅ Загружаем эмбеддинги из: {vector_file}")
    print(f"✅ Загружаем метаданные из: {meta_file}")
    
    # Загружаем эмбеддинги
    data = np.load(vector_file)
    embeddings = data["embeddings"]
    print(f"✅ Загружено {len(embeddings)} эмбеддингов")

    # Загружаем метаданные
    with open(meta_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    print(f"✅ Загружено {len(metadata)} метаданных")

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


if __name__ == "__main__":
    # Загружаем данные
    embeddings, metadata = load_data()

    # Пример запроса
    query = "что значит выиграл/проиграл концовок?"
    results = search(query, embeddings, metadata, top_k=3)

    print("🔎 Результаты поиска:")
    for r in results:
        print(f"[{r['score']:.3f}] {r['text']}")



