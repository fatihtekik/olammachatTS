# 🔍 План векторной системы ANOMALY DETECTION для фрода

## 📊 Текущая проблема
**У нас НЕТ размеченной базы мошенников** (нет ground truth), поэтому классический supervised learning не подходит.

## 🎯 РЕШЕНИЕ: Unsupervised Anomaly Detection

Вместо "обучения на мошенниках" делаем **детекцию аномалий**:
1. Векторизуем ВСЕ матчи и игроков (без разметки)
2. Строим "профиль нормального поведения"
3. Ищем **статистические выбросы** (outliers) - они и есть подозрительные
4. Кластеризуем аномалии - находим ТИПЫ мошенничества автоматически

## 🎯 Что векторизовать для anomaly detection

## 🎯 Что векторизовать для anomaly detection

### 1️⃣ **Векторизация КАЖДОГО матча** (без разметки)

Создаем вектор для КАЖДОГО матча в базе:

```python
match_vector = {
    # === КОНТЕКСТ ===
    'rating_difference': -250,        # разница рейтингов
    'is_favorite': 1,                 # этот игрок фаворит?
    'rating_percentile': 0.75,        # процентиль рейтинга (топ 25%)
    'opponent_rating_percentile': 0.45,
    
    # === РЕЗУЛЬТАТ ===
    'won': 0,                         # выиграл?
    'sets_won': 1,                    # сколько сетов взял
    'sets_lost': 3,                   # сколько проиграл
    'total_points_won': 35,
    'total_points_lost': 52,
    
    # === ДИНАМИКА СЧЕТА (ключевое!) ===
    'set1_score_diff': 5,             # 11:6 → +5
    'set2_score_diff': -9,            # 2:11 → -9
    'set3_score_diff': -6,            # 5:11 → -6
    'max_lead': 5,                    # максимальное преимущество
    'max_deficit': -9,                # максимальное отставание
    'lead_to_win': 0,                 # вел → выиграл?
    'lead_to_loss': 1,                # вел → проиграл? ⚠️
    
    # === ТЕХНИЧЕСКИЕ ПОКАЗАТЕЛИ ===
    'serve_efficiency': 0.45,         # эффективность подачи
    'receive_efficiency': 0.38,       # эффективность приема
    'serve_vs_avg': -0.25,            # отклонение от своей средней
    'receive_vs_avg': -0.30,          # отклонение от своей средней
    
    # === ВРЕМЕННОЙ КОНТЕКСТ ===
    'time_of_day': 22,                # час матча (22:00 → подозрительно?)
    'day_of_week': 6,                 # суббота
    'tournament_round': 'final',
    
    # === ИСТОРИЯ ВСТРЕЧ ===
    'h2h_winrate': 0.75,              # обычно выигрывал у этого
    'h2h_deviation': -0.75,           # сейчас проиграл ⚠️
    
    # === ФОРМА ===
    'recent_form_last5': 0.80,        # последние 5 матчей - 80% побед
    'performance_vs_form': -0.80      # сейчас сыграл НАМНОГО хуже ⚠️
}
```

**Размер вектора**: ~25-30 признаков на матч

---

### 2️⃣ **Агрегированные векторы игрока** (последние N матчей)

Вектор игрока = статистика за последние 20 матчей:

```python
player_vector = {
    # === БАЗОВАЯ СТАТИСТИКА ===
    'matches_played': 20,
    'win_rate': 0.55,
    'avg_rating': 1850,
    
    # === ЧАСТОТЫ АНОМАЛИЙ ===
    'upset_loss_rate': 0.15,          # % поражений от слабых
    'collapse_after_lead_rate': 0.20, # % коллапсов после лидерства
    'weak_clutch_rate': 0.35,         # % проигранных концовок
    
    # === ВОЛАТИЛЬНОСТЬ (ключевое для аномалий!) ===
    'performance_variance': 0.45,     # насколько нестабилен
    'serve_efficiency_std': 0.18,     # разброс подачи
    'rating_vs_performance': -0.30,   # играет хуже рейтинга
    
    # === ВРЕМЕННЫЕ ПАТТЕРНЫ ===
    'night_winrate': 0.30,            # винрейт ночью
    'day_winrate': 0.65,              # винрейт днем
    'time_variance': 0.35,            # разброс по времени ⚠️
    
    # === ПСИХОЛОГИЧЕСКИЕ ===
    'favorite_winrate': 0.70,         # когда фаворит
    'underdog_winrate': 0.40,         # когда андердог
    'role_gap': 0.30,                 # разница в ролях ⚠️
    
    # === ТРЕНДЫ ===
    'recent_trend': -0.25,            # последние матчи хуже
    'rating_trend': -50,              # падение рейтинга
}
```

---

### 3️⃣ **Векторы последовательностей** (temporal patterns)

Последовательность последних 10 матчей как вектор:

```python
sequence_vector = {
    # === ПАТТЕРН РЕЗУЛЬТАТОВ ===
    'result_sequence': [1,1,0,0,0,1,0,0,0,0],  # последние 10 матчей
    'win_streak': 0,                            # текущая серия побед
    'loss_streak': 3,                           # текущая серия поражений ⚠️
    
    # === ПАТТЕРН АНОМАЛИЙ ===
    'upset_sequence': [0,0,1,0,1,0,0,1,0,1],   # когда были апсеты
    'upset_frequency_last10': 0.40,             # 40% апсетов ⚠️
    'upset_acceleration': 2.0,                  # участились в 2 раза ⚠️
    
    # === ВРЕМЕННОЙ ИНТЕРВАЛ ===
    'days_between_losses': [3, 2, 4, 5],       # интервалы между поражениями
    'pattern_regularity': 0.75,                 # регулярность паттерна ⚠️
    
    # === ТРЕНД ЭФФЕКТИВНОСТИ ===
    'serve_eff_trend': [-0.05, -0.10, -0.08, -0.12],  # падает
    'serve_eff_slope': -0.03,                   # наклон тренда ⚠️
}
```

---

## 🔧 Техническая реализация: Anomaly Detection

### Подход 1: **Isolation Forest** (рекомендую для старта)

```python
# backend/langchain/anomaly_detector.py

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
import pandas as pd
from typing import Dict, List

class FraudAnomalyDetector:
    def __init__(self):
        self.match_scaler = StandardScaler()
        self.player_scaler = StandardScaler()
        
        # Isolation Forest для детекции аномалий
        self.match_detector = IsolationForest(
            contamination=0.05,      # ожидаем 5% аномальных матчей
            random_state=42,
            n_estimators=100
        )
        
        self.player_detector = IsolationForest(
            contamination=0.10,      # ожидаем 10% подозрительных игроков
            random_state=42,
            n_estimators=100
        )
        
        self.is_fitted = False
    
    def fit_on_all_data(self, matches_df: pd.DataFrame, players_df: pd.DataFrame):
        """
        Обучаем детектор на ВСЕХ данных (без разметки)
        Модель научится понимать "норму"
        """
        print("🔄 Обучение детектора аномалий...")
        
        # === 1. Векторизуем ВСЕ матчи ===
        match_vectors = []
        for _, match in matches_df.iterrows():
            vector = self._vectorize_match(match)
            match_vectors.append(vector)
        
        match_vectors = np.array(match_vectors)
        
        # Нормализуем
        match_vectors_scaled = self.match_scaler.fit_transform(match_vectors)
        
        # Обучаем детектор
        self.match_detector.fit(match_vectors_scaled)
        print(f"✅ Обучено на {len(match_vectors)} матчах")
        
        # === 2. Векторизуем ВСЕХ игроков ===
        player_vectors = []
        for _, player in players_df.iterrows():
            vector = self._vectorize_player(player)
            player_vectors.append(vector)
        
        player_vectors = np.array(player_vectors)
        player_vectors_scaled = self.player_scaler.fit_transform(player_vectors)
        
        self.player_detector.fit(player_vectors_scaled)
        print(f"✅ Обучено на {len(player_vectors)} игроках")
        
        self.is_fitted = True
    
    def detect_match_anomaly(self, match: Dict) -> Dict:
        """
        Определяет, является ли матч аномальным
        Возвращает anomaly_score от 0 до 1 (чем выше, тем подозрительнее)
        """
        if not self.is_fitted:
            raise ValueError("❌ Детектор не обучен! Вызовите fit_on_all_data()")
        
        # Векторизуем матч
        vector = self._vectorize_match(match)
        vector_scaled = self.match_scaler.transform([vector])
        
        # Получаем anomaly score
        # В Isolation Forest: -1 = аномалия, 1 = нормальный
        prediction = self.match_detector.predict(vector_scaled)[0]
        
        # Получаем decision function (чем ниже, тем аномальнее)
        decision = self.match_detector.decision_function(vector_scaled)[0]
        
        # Нормализуем в [0, 1] где 1 = самая большая аномалия
        anomaly_score = self._normalize_anomaly_score(decision)
        
        # Интерпретируем результат
        is_anomaly = prediction == -1
        
        return {
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': float(anomaly_score),
            'risk_level': self._get_risk_level(anomaly_score),
            'explanation': self._explain_match_anomaly(match, vector, anomaly_score)
        }
    
    def detect_player_anomaly(self, player_stats: Dict) -> Dict:
        """
        Определяет, является ли игрок аномальным (подозрительным)
        """
        if not self.is_fitted:
            raise ValueError("❌ Детектор не обучен!")
        
        vector = self._vectorize_player(player_stats)
        vector_scaled = self.player_scaler.transform([vector])
        
        prediction = self.player_detector.predict(vector_scaled)[0]
        decision = self.player_detector.decision_function(vector_scaled)[0]
        anomaly_score = self._normalize_anomaly_score(decision)
        
        return {
            'is_anomaly': bool(prediction == -1),
            'anomaly_score': float(anomaly_score),
            'risk_level': self._get_risk_level(anomaly_score),
            'explanation': self._explain_player_anomaly(player_stats, vector, anomaly_score)
        }
    
    def find_similar_anomalies(self, match_vector: np.ndarray, top_k=5) -> List[Dict]:
        """
        Находит похожие аномальные матчи (уже после обучения)
        """
        # Сравниваем с другими аномалиями из обучающей выборки
        # (можно хранить аномалии отдельно после fit)
        pass
    
    def _vectorize_match(self, match: Dict) -> np.ndarray:
        """Преобразует матч в вектор признаков"""
        
        features = [
            # Контекст
            match.get('rating_difference', 0) / 1000,
            match.get('is_favorite', 0),
            match.get('rating_percentile', 0.5),
            
            # Результат
            match.get('won', 0),
            match.get('sets_won', 0),
            match.get('sets_lost', 0),
            
            # Динамика счета (КЛЮЧЕВОЕ!)
            match.get('set1_score_diff', 0) / 11,
            match.get('set2_score_diff', 0) / 11,
            match.get('set3_score_diff', 0) / 11,
            match.get('lead_to_loss', 0),  # ⚠️ ОЧЕНЬ ПОДОЗРИТЕЛЬНО
            
            # Технические
            match.get('serve_efficiency', 0.5),
            match.get('receive_efficiency', 0.5),
            match.get('serve_vs_avg', 0),   # ⚠️ падение эффективности
            match.get('receive_vs_avg', 0),
            
            # Временные
            match.get('time_of_day', 12) / 24,
            match.get('day_of_week', 3) / 7,
            
            # История
            match.get('h2h_deviation', 0),  # ⚠️ отклонение от обычного
            match.get('performance_vs_form', 0),  # ⚠️ играл хуже формы
        ]
        
        return np.array(features)
    
    def _vectorize_player(self, player_stats: Dict) -> np.ndarray:
        """Преобразует статистику игрока в вектор"""
        
        features = [
            # Базовая статистика
            player_stats.get('win_rate', 0.5),
            player_stats.get('avg_rating', 1500) / 3000,
            
            # Частоты аномалий (КЛЮЧЕВОЕ!)
            player_stats.get('upset_loss_rate', 0),      # ⚠️
            player_stats.get('collapse_after_lead_rate', 0),  # ⚠️
            player_stats.get('weak_clutch_rate', 0),
            
            # Волатильность (КЛЮЧЕВОЕ!)
            player_stats.get('performance_variance', 0),  # ⚠️ нестабильность
            player_stats.get('serve_efficiency_std', 0),
            player_stats.get('rating_vs_performance', 0),
            
            # Временные паттерны
            player_stats.get('time_variance', 0),        # ⚠️ разброс по времени
            
            # Психологические
            player_stats.get('role_gap', 0),             # ⚠️ разница фаворит/андердог
            
            # Тренды
            player_stats.get('recent_trend', 0),
            player_stats.get('rating_trend', 0) / 500,
        ]
        
        return np.array(features)
    
    def _normalize_anomaly_score(self, decision_value: float) -> float:
        """
        Нормализует decision function в [0, 1]
        decision_value обычно в диапазоне [-0.5, 0.5]
        """
        # Чем ниже decision, тем аномальнее
        # Преобразуем так, чтобы 1 = максимальная аномалия
        normalized = 1 / (1 + np.exp(decision_value * 10))  # sigmoid
        return float(np.clip(normalized, 0, 1))
    
    def _get_risk_level(self, anomaly_score: float) -> str:
        """Преобразует anomaly_score в категорию риска"""
        if anomaly_score >= 0.8:
            return "КРИТИЧЕСКИЙ"
        elif anomaly_score >= 0.6:
            return "ВЫСОКИЙ"
        elif anomaly_score >= 0.4:
            return "СРЕДНИЙ"
        else:
            return "НИЗКИЙ"
    
    def _explain_match_anomaly(self, match: Dict, vector: np.ndarray, score: float) -> str:
        """Объясняет, почему матч аномальный"""
        reasons = []
        
        # Проверяем ключевые признаки
        if match.get('lead_to_loss', 0) == 1:
            reasons.append("Коллапс после лидерства")
        
        if match.get('serve_vs_avg', 0) < -0.2:
            reasons.append(f"Падение эффективности подачи на {abs(match['serve_vs_avg'])*100:.0f}%")
        
        if match.get('h2h_deviation', 0) < -0.5:
            reasons.append("Неожиданное поражение от этого соперника")
        
        if match.get('performance_vs_form', 0) < -0.5:
            reasons.append("Выступил намного хуже своей формы")
        
        if match.get('time_of_day', 12) >= 22 or match.get('time_of_day', 12) <= 6:
            reasons.append("Матч в нетипичное время (ночь)")
        
        if not reasons:
            reasons.append("Комбинация статистических отклонений")
        
        return "; ".join(reasons)
    
    def _explain_player_anomaly(self, player_stats: Dict, vector: np.ndarray, score: float) -> str:
        """Объясняет, почему игрок аномальный"""
        reasons = []
        
        if player_stats.get('upset_loss_rate', 0) > 0.20:
            reasons.append(f"Высокая частота поражений от слабых ({player_stats['upset_loss_rate']*100:.0f}%)")
        
        if player_stats.get('collapse_after_lead_rate', 0) > 0.25:
            reasons.append(f"Частые коллапсы после лидерства ({player_stats['collapse_after_lead_rate']*100:.0f}%)")
        
        if player_stats.get('performance_variance', 0) > 0.40:
            reasons.append("Высокая нестабильность выступлений")
        
        if player_stats.get('time_variance', 0) > 0.30:
            reasons.append("Большой разброс результатов по времени суток")
        
        if player_stats.get('role_gap', 0) > 0.35:
            reasons.append("Большая разница в игре за фаворита/андердога")
        
        if not reasons:
            reasons.append("Комбинация поведенческих паттернов")
        
        return "; ".join(reasons)


# === ИСПОЛЬЗОВАНИЕ ===

def train_anomaly_detector():
    """Обучает детектор на всех данных"""
    from app.database import get_session
    from app.models import Match, Player
    import pandas as pd
    
    session = get_session()
    detector = FraudAnomalyDetector()
    
    # Загружаем ВСЕ матчи
    matches = session.query(Match).all()
    matches_df = pd.DataFrame([
        extract_match_features(m) for m in matches
    ])
    
    # Загружаем ВСЕХ игроков
    players = session.query(Player).all()
    players_df = pd.DataFrame([
        calculate_player_stats(p, session) for p in players
    ])
    
    # Обучаем
    detector.fit_on_all_data(matches_df, players_df)
    
    # Сохраняем модель
    import joblib
    joblib.dump(detector, 'backend/langchain/anomaly_detector.pkl')
    print("✅ Модель сохранена")
    
    return detector


def extract_match_features(match: Match) -> Dict:
    """Извлекает признаки из матча для векторизации"""
    # ... расчет всех признаков из match_vector выше
    pass


def calculate_player_stats(player: Player, session) -> Dict:
    """Вычисляет статистику игрока для векторизации"""
    # ... расчет всех признаков из player_vector выше
    pass
```

---

### Подход 2: **Autoencoder** (более продвинутый)

```python
import torch
import torch.nn as nn

class AnomalyAutoencoder(nn.Module):
    """
    Автоэнкодер для детекции аномалий
    Учится сжимать и восстанавливать НОРМАЛЬНЫЕ матчи
    Аномальные матчи будут восстанавливаться с большой ошибкой
    """
    def __init__(self, input_dim=25):
        super().__init__()
        
        # Encoder: сжимаем вектор
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 4)  # bottleneck
        )
        
        # Decoder: восстанавливаем вектор
        self.decoder = nn.Sequential(
            nn.Linear(4, 8),
            nn.ReLU(),
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim)
        )
    
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded
    
    def anomaly_score(self, x):
        """
        Reconstruction error = насколько плохо восстановили
        Большая ошибка = аномалия
        """
        reconstructed = self.forward(x)
        mse = torch.mean((x - reconstructed) ** 2, dim=1)
        return mse


# Обучение: просто учим восстанавливать ВСЕ матчи
model = AnomalyAutoencoder()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
criterion = nn.MSELoss()

for epoch in range(100):
    for batch in dataloader:
        reconstructed = model(batch)
        loss = criterion(reconstructed, batch)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

# Детекция: большая reconstruction error = аномалия
anomaly_scores = model.anomaly_score(new_matches)
```

---

### Подход 3: **DBSCAN Clustering**
```

---

```

Кластеры аномалий:
- Density-based кластеризация → автоматически находит "типы" мошенничества
- Noise points = самые странные случаи

---

## 📈 Как это работает БЕЗ разметки

### 🎯 Главная идея:

**Нормальные матчи образуют "плотное облако" в векторном пространстве**  
**Аномалии (мошенничество) - это точки далеко от облака**

### Пример:

```
Нормальные матчи:
  • Фаворит выиграл с нормальной эффективностью → вектор [0.5, 0.7, 0.6, ...]
  • Андердог проиграл после борьбы → вектор [0.4, 0.6, 0.5, ...]
  • Равный матч, выиграл сильнейший → вектор [0.5, 0.65, 0.55, ...]
  
  ⬇️ Все эти векторы близко друг к другу
  
Аномальный матч:
  • Фаворит (+300 рейтинга) вел 2:0, потом слил 3 сета 2-11, 3-11, 5-11
  • Эффективность подачи упала с 0.75 до 0.35
  • Это было ночью в субботу
  
  → вектор [0.1, 0.2, 0.15, ...] 
  
  ⬇️ Далеко от облака нормальных матчей! ⚠️
```

### 📊 Что делает Isolation Forest:

1. Берет случайный признак (например, serve_vs_avg)
2. Делит пространство: левая часть, правая часть
3. Повторяет много раз
4. Аномалии изолируются БЫСТРО (за 3-4 деления)
5. Нормальные точки требуют много делений

**Результат**: Аномалии получают высокий anomaly_score

---

## 📈 Ожидаемые результаты (Unsupervised)

### ✅ Преимущества без размеченных данных:

1. **Автоматическое обнаружение**: Не нужна ручная разметка "мошенник/не мошенник"
2. **Обнаружение новых схем**: Найдет аномалии, которые мы не предусмотрели в правилах
3. **Количественная оценка**: anomaly_score от 0 до 1 (не бинарное да/нет)
4. **Кластеризация типов**: Автоматически группирует похожие аномалии → находит ТИПЫ фрода
5. **Эволюция**: Модель адаптируется при добавлении новых данных

### 📊 Что получим на выходе:

**Для каждого триггера:**
```python
{
    'is_anomaly': True,           # Да, это аномалия
    'anomaly_score': 0.87,        # 87% уверенности
    'risk_level': 'КРИТИЧЕСКИЙ',
    'explanation': 'Коллапс после лидерства; Падение эффективности подачи на 35%; Неожиданное поражение',
    'similar_cases': [            # Похожие случаи из истории
        {'player': 'Игрок X', 'date': '2024-05-12', 'similarity': 0.92},
        {'player': 'Игрок Y', 'date': '2024-08-03', 'similarity': 0.88}
    ],
    'cluster_type': 'controlled_collapse'  # Автоматически определенный тип
}
```

### 🎯 Типичные кластеры аномалий (находятся автоматически):

1. **Кластер "Контролируемый коллапс"**
   - Лидерство 2:0 → слив 3го сета
   - Падение serve_efficiency на 30%+
   - Обычно вечер/ночь

2. **Кластер "Серийные апсеты"**
   - Поражения от слабых с интервалом 3-5 дней
   - Стабильный механизм (одинаковый счет)
   - Низкая волатильность (слишком предсказуемо)

3. **Кластер "Слив концовок"**
   - Нормальная игра до 10-10
   - Резкое падение после
   - Повторяется регулярно

### 🔍 Workflow использования:

```
1. Обучаем на ВСЕХ исторических данных (без разметки)
   ↓
2. Детектор учится "что такое норма"
   ↓
3. При новом триггере: вычисляем anomaly_score
   ↓
4. Если anomaly_score > 0.7 → ⚠️ ПОДОЗРИТЕЛЬНО
   ↓
5. AI анализирует с контекстом: "anomaly_score 0.87, похож на кластер 'controlled_collapse'"
   ↓
6. Получаем обоснованный вердикт AI
```

---

## 🚀 Минимальная реализация (MVP) - ЧТО ДЕЛАТЬ СЕЙЧАС

### Задача: Добавить anomaly_score в AI анализ

Вместо полноценной векторной системы, **начнем с простого**:

#### Шаг 1: Добавить расчет "подозрительности" (1-2 часа)

```python
# backend/app/services/match_analysis_service.py

def _calculate_suspicion_score(self, player_stats: Dict) -> float:
    """
    Простой скоринг подозрительности БЕЗ ML
    Возвращает 0-1, где 1 = максимально подозрительно
    """
    score = 0.0
    
    # 1. Поражения от слабых (вес 0.25)
    upset_rate = player_stats.get('opponent_analysis', {}).get('vs_weaker_winrate', 1.0)
    if upset_rate < 0.50:  # винрейт против слабых < 50%
        score += 0.25 * (1 - upset_rate)
    
    # 2. Коллапсы после лидерства (вес 0.30)
    collapse_rate = player_stats.get('collapse_rate', 0)  # нужно добавить
    score += 0.30 * collapse_rate
    
    # 3. Падение эффективности (вес 0.20)
    serve_drop = player_stats.get('serve_efficiency_variance', 0)
    if serve_drop > 0.20:  # разброс > 20%
        score += 0.20 * (serve_drop / 0.5)  # нормализуем к 50%
    
    # 4. Временные аномалии (вес 0.15)
    time_variance = player_stats.get('time_performance', {})
    night_wr = time_variance.get('night_winrate', 0.5)
    day_wr = time_variance.get('day_winrate', 0.5)
    if abs(night_wr - day_wr) > 0.30:  # разница > 30%
        score += 0.15
    
    # 5. Нестабильность в роли (вес 0.10)
    role_perf = player_stats.get('role_performance', {})
    favorite_wr = role_perf.get('as_favorite', 0.5)
    underdog_wr = role_perf.get('as_underdog', 0.5)
    if favorite_wr > 0 and underdog_wr > 0:
        role_gap = abs(favorite_wr - underdog_wr)
        if role_gap > 0.40:  # разница > 40%
            score += 0.10
    
    return min(score, 1.0)  # ограничиваем [0, 1]
```

#### Шаг 2: Добавить в промпт AI (10 минут)

```python
def _create_analysis_prompt(self, player_name: str, trigger_value: str, player_stats: Dict) -> str:
    # Вычисляем suspicion_score
    suspicion_score = self._calculate_suspicion_score(player_stats)
    risk_emoji = "🔴" if suspicion_score > 0.7 else "🟠" if suspicion_score > 0.5 else "🟡" if suspicion_score > 0.3 else "🟢"
    
    prompt = f"""
🚨 АНАЛИЗ ТРИГГЕРА

📋 ИГРОК: {player_name}
📊 ТРИГГЕР: {trigger_value}

⚠️ АВТОМАТИЧЕСКИЙ СКОРИНГ ПОДОЗРИТЕЛЬНОСТИ:
{risk_emoji} Уровень подозрительности: {suspicion_score:.2%}

Детализация:
  • Поражения от слабых: {player_stats.get('opponent_analysis', {}).get('vs_weaker_winrate', 1.0):.0%} винрейт
  • Коллапсы после лидерства: {player_stats.get('collapse_rate', 0):.0%}
  • Разброс эффективности подачи: ±{player_stats.get('serve_efficiency_variance', 0):.0%}
  • Разница день/ночь: {abs(player_stats.get('time_performance', {}).get('night_winrate', 0.5) - player_stats.get('time_performance', {}).get('day_winrate', 0.5)):.0%}

� СТАТИСТИКА:
...

❗ ЗАДАЧА:
Учитывая автоматический скоринг подозрительности {suspicion_score:.0%}, проанализируй:
- 🚨 УРОВЕНЬ РИСКА
- 📊 КЛЮЧЕВЫЕ АНОМАЛИИ
- 🎯 ВЕРОЯТНАЯ СХЕМА
- ✅ РЕКОМЕНДАЦИИ
"""
    return prompt
```

#### Шаг 3: Добавить недостающие метрики (2-3 часа)

Нужно добавить в `_get_player_stats_for_trigger()`:

```python
# Расчет collapse_rate
def _calculate_collapse_rate(self, player_id: str, matches: List[Match]) -> float:
    """Процент матчей где игрок вел 2:0 и проиграл"""
    collapses = 0
    total_lead_situations = 0
    
    for match in matches:
        is_player1 = match.player1_id == player_id
        
        # Проверяем, была ли ситуация лидерства 2:0
        if is_player1 and match.sets_won_player1 >= 2:
            total_lead_situations += 1
            if match.sets_won_player2 > match.sets_won_player1:  # проиграл после лидерства
                collapses += 1
        elif not is_player1 and match.sets_won_player2 >= 2:
            total_lead_situations += 1
            if match.sets_won_player1 > match.sets_won_player2:
                collapses += 1
    
    return collapses / total_lead_situations if total_lead_situations > 0 else 0

# Расчет serve_efficiency_variance
def _calculate_serve_efficiency_variance(self, player_id: str, matches: List[Match]) -> float:
    """Разброс эффективности подачи (стандартное отклонение)"""
    serve_efficiencies = []
    
    for match in matches:
        is_player1 = match.player1_id == player_id
        serve_eff = match.serve_efficiency_p1 if is_player1 else match.serve_efficiency_p2
        
        if serve_eff is not None:
            serve_efficiencies.append(serve_eff)
    
    if len(serve_efficiencies) < 3:
        return 0
    
    return float(np.std(serve_efficiencies))
```

---

## 🎯 Полноценная векторная система (позже)

### Этапы внедрения

### Фаза 1: Подготовка (1-2 дня)
- [ ] Создать `anomaly_detector.py` с Isolation Forest
- [ ] Реализовать все функции расчета фрод-метрик
- [ ] Протестировать детекцию на 100 матчах

### Фаза 2: Обучение модели (1 день)
- [ ] Создать `train_anomaly_detector.py`
- [ ] Извлечь все матчи из БД и векторизовать
- [ ] Обучить Isolation Forest
- [ ] Сохранить модель в `anomaly_detector.pkl`

### Фаза 3: Интеграция (1 день)
- [ ] Загружать модель при старте сервиса
- [ ] Добавить anomaly_score в `_create_analysis_prompt`
- [ ] Обновить UI: показывать anomaly_score с цветовой индикацией
- [ ] Протестировать на реальных триггерах

### Фаза 4: Кластеризация (опционально, 1-2 дня)
- [ ] Применить DBSCAN к найденным аномалиям
- [ ] Автоматически найти "типы" мошенничества
- [ ] Присвоить каждому кластеру имя (на основе общих признаков)
- [ ] Показывать: "Тип аномалии: Контролируемый коллапс (кластер #3)"

---

## 💡 Дополнительные идеи (будущее)

### 🔮 Temporal Patterns (временные последовательности)
Вместо одного матча - анализируем последовательность:
- LSTM/Transformer на последовательности векторов последних 10 матчей
- Предсказание: вероятность следующего триггера в течение 7 дней
- "Эскалация": частота триггеров растет → риск увеличивается

### 🌐 Граф связей игроков
Network Analysis:
- Кто с кем часто играет подозрительные матчи
- Community detection → находим группы взаимодействующих мошенников
- PageRank → центральные фигуры в схемах

### 📸 Визуализация
- t-SNE проекция векторов игроков в 2D
- Интерактивная карта: нормальные (зеленые точки) vs аномалии (красные)
- Hover → детали игрока
- Клик → подробный анализ

---

## ❓ Резюме: Что делать СЕЙЧАС vs ПОТОМ

### 🎯 СЕЙЧАС (MVP за 3-5 часов):
1. Добавить простой `_calculate_suspicion_score()` - rule-based скоринг
2. Добавить недостающие метрики: `collapse_rate`, `serve_efficiency_variance`
3. Передать suspicion_score в AI промпт
4. AI использует его как дополнительный контекст

**Результат**: AI получает численную оценку подозрительности и учитывает её в анализе

### 🚀 ПОТОМ (когда MVP работает):
1. Собрать исторические данные в датафрейм
2. Обучить Isolation Forest на всех матчах
3. Получать anomaly_score из модели (вместо rule-based)
4. Кластеризовать аномалии → автоматически найти типы фрода

**Результат**: Полноценная ML-система с автоматическим обнаружением новых схем

---

Начать с MVP? Это быстро и сразу улучшит анализ! 🚀
