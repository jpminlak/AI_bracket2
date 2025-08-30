from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tensorflow as tf
from PIL import Image
import numpy as np
import io
import pandas as pd
import os
import joblib

# YOLOv5 로드
try:
    from ultralytics import YOLO
    YOLO_MODEL_PATH = "model/food_detector_v1 (1).pt"
    if not os.path.exists(YOLO_MODEL_PATH):
        raise FileNotFoundError(f"YOLO 모델 파일이 없습니다: {YOLO_MODEL_PATH}")
    yolo_model = YOLO(YOLO_MODEL_PATH)
    print(f"✅ YOLOv5 모델 로드 성공: {YOLO_MODEL_PATH}")
except ImportError:
    YOLO = None
    yolo_model = None
    print("❌ Ultralytics 라이브러리가 설치되어 있지 않습니다.")
except FileNotFoundError as e:
    yolo_model = None
    print(f"❌ {e}")
except Exception as e:
    yolo_model = None
    print(f"❌ YOLO 모델 로드 오류: {e}")

app = FastAPI()

# 모델 파일 경로 - EfficientNet-B0 모델로 변경됨!
CLASSIFIER_MODEL_PATH = "model/food_classifier_model_mbnet(ver1).h5"
CALORIE_SCALER_PATH = "model/food_scaler.pkl"
CALORIE_MODEL_PATH = "model/food_model.keras"

# 1. EfficientNet-B0 분류 모델 로드
try:
    if not os.path.exists(CLASSIFIER_MODEL_PATH):
        raise FileNotFoundError(f"분류 모델 파일이 없습니다: {CLASSIFIER_MODEL_PATH}")
    classifier_model = tf.keras.models.load_model(CLASSIFIER_MODEL_PATH)
    print(f"✅ EfficientNet-B0 모델 로드 성공: {CLASSIFIER_MODEL_PATH}")
except Exception as e:
    classifier_model = None
    print(f"❌ 분류 모델 로드 실패: {e}")

# 2. 칼로리 예측 모델 로드
try:
    if not os.path.exists(CALORIE_MODEL_PATH):
        raise FileNotFoundError(f"칼로리 모델 파일이 없습니다: {CALORIE_MODEL_PATH}")
    calorie_model = tf.keras.models.load_model(CALORIE_MODEL_PATH)
    print(f"✅ 칼로리 모델 로드 성공: {CALORIE_MODEL_PATH}")
except Exception as e:
    calorie_model = None
    print(f"❌ 칼로리 모델 로드 실패: {e}")
    
# 3. 칼로리 스케일러 로드
try:
    if not os.path.exists(CALORIE_SCALER_PATH):
        raise FileNotFoundError(f"스케일러 파일이 없습니다: {CALORIE_SCALER_PATH}")
    calorie_scaler = joblib.load(CALORIE_SCALER_PATH)
    print(f"✅ 스케일러 로드 성공: {CALORIE_SCALER_PATH}")
except Exception as e:
    calorie_scaler = None
    print(f"❌ 스케일러 로드 실패: {e}")

# Food-101 클래스 이름들
CLASS_NAMES = [
    'apple_pie', 'baby_back_ribs', 'baklava', 'beef_carpaccio', 'beef_tartare',
    'beet_salad', 'beignets', 'bibimbap', 'bread_pudding', 'breakfast_burrito',
    'bruschetta', 'caesar_salad', 'cannoli', 'caprese_salad', 'carrot_cake',
    'ceviche', 'cheese_plate', 'cheesecake', 'chicken_curry', 'chicken_quesadilla',
    'chicken_wings', 'chocolate_cake', 'chocolate_mousse', 'churros',
    'clam_chowder', 'club_sandwich', 'crab_cakes', 'creme_brulee', 'croque_madame',
    'cup_cakes', 'deviled_eggs', 'donuts', 'dumplings', 'edamame', 'eggs_benedict',
    'escargots', 'falafel', 'filet_mignon', 'fish_and_chips', 'foie_gras',
    'french_fries', 'french_onion_soup', 'french_toast', 'fried_calamari',
    'fried_rice', 'frozen_yogurt', 'garlic_bread', 'gnocchi', 'greek_salad',
    'grilled_cheese_sandwich', 'grilled_salmon', 'guacamole', 'gyoza', 'hamburger',
    'hot_and_sour_soup', 'hot_dog', 'huevos_rancheros', 'hummus', 'ice_cream',
    'lasagna', 'lobster_bisque', 'lobster_roll_sandwich', 'macaroni_and_cheese',
    'macarons', 'miso_soup', 'mussels', 'nachos', 'omelette', 'onion_rings',
    'oysters', 'pad_thai', 'paella', 'pancakes', 'panna_cotta', 'peking_duck',
    'pho', 'pizza', 'pork_chop', 'poutine', 'prime_rib', 'pulled_pork_sandwich',
    'ramen', 'ravioli', 'red_velvet_cake', 'risotto', 'samosa', 'sashimi',
    'scallops', 'seaweed_salad', 'shrimp_and_grits', 'spaghetti_bolognese',
    'spaghetti_carbonara', 'spring_rolls', 'steak', 'strawberry_shortcake',
    'sushi', 'tacos', 'takoyaki', 'tiramisu', 'tuna_tartare', 'waffles'
]

def preprocess_image_for_efficientnet(image, target_size=(224, 224)):
    """EfficientNet-B0에 맞는 전처리"""
    # 수정된 부분: 흑백 변환을 제거하고 RGB 이미지를 그대로 사용합니다.
    # 모델이 3채널(RGB) 입력을 기대하기 때문입니다.
    
    # 이미지 크기 조정
    resized_image = image.resize(target_size)
    
    # 배열로 변환
    img_array = tf.keras.preprocessing.image.img_to_array(resized_image)
    img_array = np.expand_dims(img_array, axis=0)
    
    # EfficientNet 전처리: [0,255] → [-1,1] 범위로 정규화
    img_array = img_array / 255.0
    img_array = (img_array - 0.5) * 2.0
    
    print(f"🔧 전처리 완료 - 이미지 형태: {img_array.shape}")
    return img_array

@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "service": "음식 분석 API v2",
        "status": "running",
        "models": {
            "yolo": "로드됨" if yolo_model else "로드 안됨",
            "classifier": "로드됨" if classifier_model else "로드 안됨",
            "calorie": "로드됨" if calorie_model else "로드 안됨",
            "scaler": "로드됨" if calorie_scaler else "로드 안됨"
        }
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # 모델 상태 확인
    if classifier_model is None:
        raise HTTPException(status_code=500, detail="분류 모델이 로드되지 않았습니다.")
    
    if yolo_model is None:
        raise HTTPException(status_code=500, detail="YOLO 모델이 로드되지 않았습니다.")

    try:
        contents = await file.read()
        # 수정된 부분: convert("RGB")를 사용해 이미지 형식을 확실히 합니다.
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        print(f"📷 이미지 크기: {image.size}")

        # 1. YOLO로 음식 객체 감지
        yolo_results = yolo_model(image)
        
        detected_food_names = []
        for result in yolo_results:
            if hasattr(result, 'boxes') and len(result.boxes) > 0:
                if hasattr(yolo_model, 'names'):
                    detected_classes = [yolo_model.names[int(c)] for c in result.boxes.cls]
                    detected_food_names.extend(detected_classes)
                    print(f"🔍 YOLO 감지: {detected_classes}")
                else:
                    print("⚠️ YOLO 모델에 클래스 이름 정보가 없습니다.")
        
        if not detected_food_names:
            print("⚠️ 이미지에서 음식을 감지하지 못했습니다.")
            # 감지 실패해도 분류는 시도
            detected_food_names = ["unknown"]

        # 2. EfficientNet-B0으로 정확한 음식 분류 
        # ✅ EfficientNet에 맞는 전처리 사용
        img_array = preprocess_image_for_efficientnet(image)

        classifier_predictions = classifier_model.predict(img_array)
        scores = tf.nn.softmax(classifier_predictions[0])
        
        # 상위 5개 결과 가져오기
        top_5_indices = np.argsort(scores)[-5:][::-1]
        top_predictions = []
        
        for idx in top_5_indices:
            food_name = CLASS_NAMES[idx]
            confidence = float(scores[idx])
            top_predictions.append({
                "name": food_name,
                "confidence": confidence,
                "korean_name": food_name.replace('_', ' ').title()
            })
            print(f"🍽️ {food_name}: {confidence:.3f}")

        # 3. 칼로리 예측 (가능한 경우)
        predicted_calories = None
        if calorie_model is not None and calorie_scaler is not None:
            try:
                # 칼로리 모델 입력 준비 (feature engineering 필요할 수 있음)
                # 여기서는 단순하게 이미지 특성만 사용
                calorie_input = img_array.reshape(1, -1)  # 평평하게 만들기
                
                # 스케일러 적용
                calorie_input_scaled = calorie_scaler.transform(calorie_input)
                
                # 칼로리 예측
                calorie_pred = calorie_model.predict(calorie_input_scaled)
                predicted_calories = float(calorie_pred[0][0]) if len(calorie_pred[0]) > 0 else None
                print(f"🔥 예측 칼로리: {predicted_calories}")
                
            except Exception as e:
                print(f"❌ 칼로리 예측 실패: {e}")
                predicted_calories = None

        # 응답 구성
        response = {
            "detected_food_names": detected_food_names,
            "classified_food": {
                "name": top_predictions[0]["name"],
                "korean_name": top_predictions[0]["korean_name"], 
                "confidence": top_predictions[0]["confidence"],
                "alternatives": top_predictions[1:3],  # 상위 2개 대안
                "nutrition": {},
                "predicted_calories": predicted_calories
            },
            "debug_info": {
                "yolo_detected": detected_food_names,
                "top_5_predictions": top_predictions,
                "image_size": image.size
            }
        }

        return JSONResponse(content=response)

    except Exception as e:
        print(f"❌ 전체 처리 오류: {e}")
        raise HTTPException(status_code=400, detail=f"이미지 처리 오류: {e}")

@app.post("/debug")
async def debug_model(file: UploadFile = File(...)):
    """모델 디버깅용 엔드포인트"""
    if classifier_model is None:
        raise HTTPException(status_code=500, detail="분류 모델이 로드되지 않았습니다.")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # 원본 MobileNetV2 전처리 (컬러용)
        img_array_mobile = tf.keras.preprocessing.image.img_to_array(image.resize((224, 224)))
        img_array_mobile = np.expand_dims(img_array_mobile, axis=0)
        img_array_mobile = tf.keras.applications.mobilenet_v2.preprocess_input(img_array_mobile)
        
        # EfficientNet 전처리 (수정된 컬러용)  
        img_array_efficient = preprocess_image_for_efficientnet(image)
        
        # 두 전처리 방식으로 각각 예측
        pred_mobile = classifier_model.predict(img_array_mobile)
        pred_efficient = classifier_model.predict(img_array_efficient)
        
        scores_mobile = tf.nn.softmax(pred_mobile[0])
        scores_efficient = tf.nn.softmax(pred_efficient[0])
        
        return {
            "mobile_preprocessing": {
                "top_class": CLASS_NAMES[np.argmax(scores_mobile)],
                "confidence": float(np.max(scores_mobile)),
                "top_3": [(CLASS_NAMES[i], float(scores_mobile[i])) 
                         for i in np.argsort(scores_mobile)[-3:][::-1]]
            },
            "efficient_preprocessing": {
                "top_class": CLASS_NAMES[np.argmax(scores_efficient)],
                "confidence": float(np.max(scores_efficient)),
                "top_3": [(CLASS_NAMES[i], float(scores_efficient[i])) 
                         for i in np.argsort(scores_efficient)[-3:][::-1]]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"디버깅 오류: {e}")
