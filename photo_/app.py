import io
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image as keras_image
import pandas as pd

# =========================================================
# 모델과 영양 DB 로드
# =========================================================
# ⚠️ 실제 파일 경로에 맞게 수정해야 합니다.
# 예시: 'model/foodim4.keras'와 'dataset/food.csv'
MODEL_PATH = "model/foodim9.keras"
NUTRITION_DB_PATH = "dataset/food.csv"

try:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"모델 파일이 존재하지 않습니다: {MODEL_PATH}")
    # `compile=False`를 사용하여 MobileNetV2 모델 로드 시 발생할 수 있는 오류 방지
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    print("✅ 모델 로드 완료!")
except Exception as e:
    model = None
    print(f"❌ 모델 로드 실패: {e}")

try:
    if not os.path.exists(NUTRITION_DB_PATH):
        raise FileNotFoundError(f"영양 DB 파일이 존재하지 않습니다: {NUTRITION_DB_PATH}")
    # BOM 제거 위해 utf-8-sig 사용
    nutrition_db = pd.read_csv(NUTRITION_DB_PATH, encoding='utf-8-sig')
    print("✅ 영양 DB 로드 완료!")
except Exception as e:
    nutrition_db = None
    print(f"❌ 영양 DB 로드 실패: {e}")

# =========================================================
# 클래스 이름 (모델 예측 클래스와 일치해야 합니다)
# =========================================================
CLASS_NAMES = ['.ipynb_checkpoints', '고사리나물', '곱창전골', '김치전',
               '깍두기', '달걀국', '달걀말이', '돼지갈비', '양념치킨', '전복죽', '호박전', '훈제오리']

# =========================================================
# FastAPI 앱 생성
# =========================================================
app = FastAPI(title="음식 분류 + 영양 API")

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# 이미지 전처리
# =========================================================
def preprocess_image(image: Image.Image, target_size=(224, 224)):
    """Gradio에서 사용된 전처리 로직을 FastAPI에 맞게 재구성합니다."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    image = image.resize(target_size)
    
    img_array = keras_image.img_to_array(image)
    
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0
    
    return img_array

# =========================================================
# 루트 엔드포인트
# =========================================================
@app.get("/")
async def root():
    return {"message": "음식 분류 + 영양 API가 실행 중입니다."}

# =========================================================
# 음식 이미지 업로드 및 분석
# =========================================================
@app.post("/upload")
async def predict_food(file: UploadFile = File(...)):
    if model is None or nutrition_db is None:
        raise HTTPException(status_code=500, detail="모델 또는 영양 DB가 로드되지 않았습니다.")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        preprocessed = preprocess_image(image)
        
        preds = model.predict(preprocessed)
        class_idx = int(np.argmax(preds[0]))
        predicted_food = CLASS_NAMES[class_idx]
        confidence = float(np.max(preds[0]))

        # 🔹 공백 제거 후 CSV 매칭
        predicted_food_clean = predicted_food.strip()
        nutrition_info_row = nutrition_db[nutrition_db['음 식 명'].str.strip() == predicted_food_clean]

        if not nutrition_info_row.empty:
            info = nutrition_info_row.iloc[0].to_dict()
            nutrition_info = {
                "calories": float(info.get("에너지(kcal)", 0)),  
                "protein": float(info.get("단백질(g)", 0)),
                "fat": float(info.get("지방(g)", 0)),
                "carbohydrates": float(info.get("탄수화물(g)", 0))
            }
        else:
            nutrition_info = {
                "calories": None,
                "protein": None,
                "fat": None,
                "carbohydrates": None
            }

        # 🔹 항상 JSON 형식으로 반환
        return JSONResponse(content={
            "food_name": predicted_food,
            "confidence": confidence,
            "nutrition_info": nutrition_info
        })

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"이미지 처리 오류: {e}")
