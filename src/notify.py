import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def send(text):
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("CHAT_ID")
    print(text)
    if not token or not chat:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat, "text": text}, timeout=20)
    except Exception as e:
        print("Telegram failed:", e)
