import requests
import time
from bs4 import BeautifulSoup

api_key = "+"
def get(self,prompt,main_rule):
    input_data = {
    "messages": []
    }

    url_endpoint = "https://api.gen-api.ru/api/v1/networks/deepseek-v4"
    headers = {'Authorization': f'Bearer {api_key}'}

    response = requests.post(url_endpoint, json=input_data, headers=headers)
    if response.status_code != 200:
        print(f"Ошибка API: {response.status_code}")
        return None

    response_json = response.json()
    request_id = response_json.get("request_id")

    # Ожидание готовности
    while True:
        response = requests.get(
            f'https://api.gen-api.ru/api/v1/request/get/{request_id}',
            headers=headers
        )
        data = response.json()

        if data.get('status') == 'success':
            url = data.get('result')[0]
            data = requests.get(url)

        elif data.get('status') == 'failed':
            return None

        time.sleep(3)