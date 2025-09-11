# main.py 파일
# pip install tensorflow==2.18
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import tensorflow as tf
from PIL import Image
from fatsecretapi import FatSecretAPIClient # fatsecretapi.py 파일로부터 클래스 임포트

app = FastAPI()

origins = [
    "http://localhost:8080"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모델 로드
MODEL_PATH = '../model/model_efB0_local_fixed.keras'


try:
    model = tf.keras.models.load_model(MODEL_PATH)
    model.summary()
    print("✅ 모델 로드 완료!")
    
except Exception as e:
    model = None
    print(f"❌ 모델 로드 실패: {e}")
        
class_names=['apple_pie', 'baby_back_ribs', 'baklava', 'beef_carpaccio', 'beef_tartare', 'beet_salad', 'beignets', 'bibimbap', 'bread_pudding', 'breakfast_burrito', 'bruschetta', 'caesar_salad', 'cannoli', 'caprese_salad', 'carrot_cake', 'ceviche', 'cheese_plate', 'cheesecake', 'chicken_curry', 'chicken_quesadilla', 'chicken_wings', 'chocolate_cake', 'chocolate_mousse', 'churros', 'clam_chowder', 'club_sandwich', 'crab_cakes', 'creme_brulee', 'croque_madame', 'cup_cakes', 'deviled_eggs', 'donuts', 'dumplings', 'edamame', 'eggs_benedict', 'escargots', 'falafel', 'filet_mignon', 'fish_and_chips', 'foie_gras', 'french_fries', 'french_onion_soup', 'french_toast', 'fried_calamari', 'fried_rice', 'frozen_yogurt', 'garlic_bread', 'gnocchi', 'greek_salad', 'grilled_cheese_sandwich', 'grilled_salmon', 'guacamole', 'gyoza', 'hamburger', 'hot_and_sour_soup', 'hot_dog', 'huevos_rancheros', 'hummus', 'ice_cream', 'lasagna', 'lobster_bisque', 'lobster_roll_sandwich', 'macaroni_and_cheese', 'macarons', 'miso_soup', 'mussels', 'nachos', 'omelette', 'onion_rings', 'oysters', 'pad_thai', 'paella', 'pancakes', 'panna_cotta', 'peking_duck', 'pho', 'pizza', 'pork_chop', 'poutine', 'prime_rib', 'pulled_pork_sandwich', 'ramen', 'ravioli', 'red_velvet_cake', 'risotto', 'samosa', 'sashimi', 'scallops', 'seaweed_salad', 'shrimp_and_grits', 'spaghetti_bolognese', 'spaghetti_carbonara', 'spring_rolls', 'steak', 'strawberry_shortcake', 'sushi', 'tacos', 'takoyaki', 'tiramisu', 'tuna_tartare', 'waffles']

# 2. FatSecret API 클라이언트 초기화
CLIENT_ID = '59be412169d845c1a8e581bdeb5c3715'
CLIENT_SECRET = '8742ec9f2fab4766b14cf50fbecee978'
fatsecret_client = FatSecretAPIClient(CLIENT_ID, CLIENT_SECRET)
fatsecret_client.get_token()

# 3. FastAPI 엔드포인트 정의
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    
    try:
        # 이미지 전처리
        image = Image.open(file.file).convert('RGB').resize((224, 224))
        image_array = np.array(image)  # 픽셀 값 정규화
        image_array = np.expand_dims(image_array, axis=0)  # 배치 차원 추가

        # 모델 예측
        predictions = model.predict(image_array)
        predicted_index = np.argmax(predictions)
        predicted_food_name = class_names[predicted_index]
        predicted_probability = float(predictions[0][predicted_index])
        # FatSecret API를 사용하여 영양 정보 검색
        food_data = fatsecret_client.search_foods(predicted_food_name)

        if not food_data:
            raise HTTPException(status_code=500, detail="API에서 영양 정보를 찾을 수 없습니다.")

        return {
            "predicted_food_name": predicted_food_name,
            "confidence": predicted_probability,
            "nutrition_info": food_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류 발생: {e}")