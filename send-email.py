import requests
from datetime import date
import os

def send_discord():
    webhook_url = os.environ["DISCORD_WEBHOOK"]
    message = f"🌅 좋은 아침입니다!\n오늘 날짜: {date.today()}"
    
    requests.post(webhook_url, json={"content": message})

send_discord()