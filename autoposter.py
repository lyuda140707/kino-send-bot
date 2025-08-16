import os
import logging
import asyncio
import random
from datetime import datetime
import pytz
from aiogram.client.default import DefaultBotProperties

from aiogram import Bot
from aiogram.enums import ParseMode

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import json

load_dotenv()

# Налаштування
BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
CHANNEL_USERNAMES = ["@KinoTochkaUA", "@KinoTochkaFilms"]
TIMEZONE = "Europe/Kyiv"

# Список випадкових підписів
FOOTERS = [
    "🎬 У нас завжди є що подивитись — слідкуй!",
    "✨ Кіно кожного дня — залишайся з нами!",
    "🎥 Підпишись, щоб не пропустити новинки!",
    "🍿 Насолоджуйся кіно — більше цікавого вже скоро!",
    "🔎 З нами знайдеш, що подивитись!",
]

# Підключення до бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=None)  # вимикаємо HTML
)

# Google Sheets авторизація
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_data = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_data), scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

async def check_and_post():
    while True:
        try:
            sheet = get_sheet()
            expected_headers = ["Текст", "Дата і час", "Оригінальне посилання", "Прямий лінк", "Статус"]
            rows = sheet.get_all_records(expected_headers=expected_headers)
            
            for idx, row in enumerate(rows, start=2):
                status = row.get("Статус", "")
                dt_str = row.get("Дата і час", "")
                text = row.get("Текст", "")
                media_url = row.get("Прямий лінк", "").strip()  # прибираємо пробіли та сміття

                if not status and dt_str and text:
                    tz = pytz.timezone(TIMEZONE)
                    dt = tz.localize(datetime.strptime(dt_str, "%Y-%m-%d %H:%M"))
                    now = datetime.now(tz)

                    if dt <= now:
                        footer = random.choice(FOOTERS)
                        final_text = f"{text}\n\n{footer}"

                        for channel in CHANNEL_USERNAMES:
                            if media_url and media_url.startswith(("BAAC", "BQAC", "CAAC")):
                                # file_id (ID медіа з Telegram)
                                await bot.send_video(chat_id=channel, video=media_url, caption=final_text)

                            elif media_url and media_url.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                                # зображення
                                await bot.send_photo(chat_id=channel, photo=media_url, caption=final_text)

                            elif media_url and media_url.lower().endswith((".mp4", ".mov", ".mkv")):
                                # відео
                                await bot.send_video(chat_id=channel, video=media_url, caption=final_text)

                            else:
                                # якщо лінка нема або він дивний — шлемо тільки текст
                                await bot.send_message(chat_id=channel, text=final_text)

                        # оновлюємо статус у таблиці
                        sheet.update_cell(idx, 5, "✅")

        except Exception as e:
            logging.error(f"Помилка: {e}")

        await asyncio.sleep(60)

        
if __name__ == "__main__":
    asyncio.run(check_and_post())
