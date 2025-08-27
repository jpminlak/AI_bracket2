# train_model.py
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, accuracy_score
import joblib

# =========================
# 1. 데이터 불러오기
# =========================
df = pd.read_csv("./data/korean_emotion_dataset.csv")

# 컬럼명 확인 후, 텍스트/라벨 지정 (데이터셋에 맞게 수정)
TEXT_COL = "Sentence"
LABEL_COL = "Emotion"

# =========================
# 2. 전처리
# =========================
def clean_text(text):
    text = re.sub(r"[^가-힣0-9\s\.\,\!\?]", "", str(text))  # 한글/숫자/기호만
    return text.strip()

df[TEXT_COL] = df[TEXT_COL].apply(clean_text)

# =========================
# 3. 데이터셋 분할
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    df[TEXT_COL], df[LABEL_COL], test_size=0.2, random_state=42, stratify=df[LABEL_COL]
)

# =========================
# 4. 벡터화 + 모델 학습
# =========================
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1,2))
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# 클래스 가중치 자동 계산
classes = df[LABEL_COL].unique()
class_weights = compute_class_weight("balanced", classes=classes, y=y_train)
class_weights_dict = {cls: w for cls, w in zip(classes, class_weights)}

model = LogisticRegression(max_iter=500, class_weight=class_weights_dict)
model.fit(X_train_vec, y_train)

# =========================
# 5. 평가
# =========================
y_pred = model.predict(X_test_vec)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))

# =========================
# 6. 모델 저장
# =========================
joblib.dump(model, "emotion_model.pkl")
joblib.dump(vectorizer, "tfidf_vectorizer.pkl")
print("✅ 모델 저장 완료: emotion_model.pkl, tfidf_vectorizer.pkl")
