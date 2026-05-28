import requests
import time
import asyncio
from telethon import TelegramClient
from bs4 import BeautifulSoup


api_key = "sk-FxRNhaFcfWRUiXWYd8kP3E0dhnrrKg4KaXXkIaYlzhwLyhFeVZzqSc5LLFFa"
def get(prompt_text):
    system_prompt = "Ты - эксперт по анализу текста на предмет его происхождения. Твоя задача - определить, является ли данное сообщение результатом работы искусственного интеллекта или написано человеком. Вероятность того, что сообщение создано ИИ, должна быть выражена числом от 0 до 1, где 0 означает, что сообщение определенно написано человеком, а 1 означает, что сообщение определенно создано ИИ. Проанализируй следующее сообщение и предоставь свою оценку вероятности: "
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt_text}
    ]
    
    input_data = {
        "messages": messages,
        "model": "deepseek-v4-flash",
        "max_tokens": 2000,
        "temperature": 0.6,
        "reasoning_effort": "none"
    }

    url_endpoint = "https://api.gen-api.ru/api/v1/networks/deepseek-v4"
    headers = {'Authorization': f'Bearer {api_key}'}

    response = requests.post(url_endpoint, json=input_data, headers=headers)
    if response.status_code != 200:
        print(f"Error API: {response.status_code}")
        return None

    response_json = response.json()
    request_id = response_json.get("request_id")

    # ожидание готовности
    while True:
        response = requests.get(
            f'https://api.gen-api.ru/api/v1/request/get/{request_id}',
            headers=headers
        )
        data = response.json()
        
        if data.get('status') == 'success':
            ai_response = data.get('result')[0]
            
            text_result = ai_response['choices'][0]['message']['content']
            
            print(text_result)
            return text_result

        elif data.get('status') == 'failed' or data.get('status') == 'error':
            print("generation failed.")
            return None

        print("Думает...", flush=True) 
        time.sleep(3)
        
get(" I'm in your butt, and that's и")