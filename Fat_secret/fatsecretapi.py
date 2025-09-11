import requests
import time
from typing import Dict, Any

class FatSecretAPIClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = 0

    def get_token(self):
        if self.access_token and self.token_expires_at > time.time():
            return
        
        
        url = 'https://oauth.fatsecret.com/connect/token'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'client_credentials',
            'scope': 'premier'
        }

        try:
            response = requests.post(
                url,
                auth=(self.client_id, self.client_secret),
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()
            token_data = response.json()
            self.access_token = response.json().get('access_token')
            self.token_expires_at = time.time() + token_data.get('expires_in', 3600)
            print("토큰 획득 및 저장 완료.")
        except requests.exceptions.RequestException as e:
            print(f"토큰 요청 중 오류 발생: {e}")


    def search_foods(self, food_name: str) -> Dict[str, Any]:
        self.get_token() # 매 호출마다 토큰 유효성 확인
        
        if not self.access_token:
            raise Exception("토큰이 없어 API를 호출할 수 없습니다.")
            return None
        method:'GET'
            
        url = 'https://platform.fatsecret.com/rest/foods/search/v3'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        params = {
            'search_expression': food_name,
            'max_results': 1,
            'page_number': 0,
            'format': 'json'
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            food_data = response.json()
            print("음식 데이터 검색 완료.")
            return food_data
        except requests.exceptions.RequestException as e:
            print(f"데이터 검색 중 오류 발생: {e}")
            return None

