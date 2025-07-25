import datetime
import requests

class WeatherAPIClient:
    def get_weather(nx,ny):
        base_date = datetime.datetime.now().strftime('%Y%m%d')
        url = (
            f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
            f"?serviceKey=sFoVQSUKX/hYO0XyMZLMj5GL8aR4w/6XmFXUnWd7LpdyL8OOREkZ9ZB1ckzaZ/y1ccGRNJxSvqFhZUJmYP3Y8A=="
            f"&pageNo=1&numOfRows=100&dataType=JSON"
            f"&base_date={base_date}&base_time=0200&nx={nx}&ny={ny}"
        )
        response = requests.get(url)
        data=response.json()
        items = data['response']['body']['items']['item']
        t1h_items = list(filter(lambda x: x['category'] == 'T1H', items))
        one=t1h_items[0]
        tem=float(one["fcstValue"])
        return tem
        