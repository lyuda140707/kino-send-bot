import os
import logging
import random
from datetime import datetime
import pytz
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import json
import traceback
load_dotenv()
from fastapi import FastAPI

# ===== Налаштування =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
CHANNEL_USERNAMES = ["@KinoTochkaUA", "@KinoTochkaFilms"]
TIMEZONE = os.getenv("TIMEZONE", "Europe/Kyiv")

FOOTERS = [
    "🎬 У нас завжди є що подивитись — слідкуй!",
    "✨ Кіно кожного дня — залишайся з нами!",
    "🎥 Підпишись, щоб не пропустити новинки!",
    "🍿 Насолоджуйся кіно — більше цікавого вже скоро!",
    "🔎 З нами знайдеш, що подивитись!",
]

# Один об'єкт бота на весь процес
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))

def get_sheet():
    import base64, json, re, logging
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    raw_b64  = (os.getenv("GOOGLE_SHEETS_CREDENTIALS_B64")  or "").strip()
    raw_json = (os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON") or "").strip()

    def _parse_b64(b64s: str):
        b64s = "".join(b64s.split())  # прибрати пробіли/перенесення
        payload = base64.b64decode(b64s, validate=False).decode("utf-8", errors="strict")
        return json.loads(payload)

    def _looks_like_b64(s: str) -> bool:
        return len(s) > 100 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", s) is not None

    try:
        if raw_b64:
            data = _parse_b64(raw_b64)
        elif raw_json:
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                if _looks_like_b64(raw_json):
                    data = _parse_b64(raw_json)
                else:
                    logging.error("GOOGLE_SHEETS_CREDENTIALS_JSON не схожий ні на JSON, ні на base64 (len=%d)", len(raw_json))
                    raise
        else:
            raise RuntimeError("Немає GOOGLE_SHEETS_CREDENTIALS_B64 і GOOGLE_SHEETS_CREDENTIALS_JSON")

        email = data.get("client_email", "")
        logging.warning("CREDS OK: client_email=***%s", email[-18:] if email else "missing")
    except Exception:
        logging.exception("Не вдалося розібрати Google credentials")
        raise

    creds = ServiceAccountCredentials.from_json_keyfile_dict(data, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1



async def send_to_channels(final_text: str, media_url: str | None):
    for channel in CHANNEL_USERNAMES:
        if media_url and media_url.startswith(("BAAC", "BQAC", "CAAC")):
            await bot.send_video(chat_id=channel, video=media_url, caption=final_text)
        elif media_url and media_url.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            await bot.send_photo(chat_id=channel, photo=media_url, caption=final_text)
        elif media_url and media_url.lower().endswith((".mp4", ".mov", ".mkv")):
            await bot.send_video(chat_id=channel, video=media_url, caption=final_text)
        else:
            await bot.send_message(chat_id=channel, text=final_text)

async def run_once():
    """Одна ітерація: знайти пости на час і відправити їх, оновити статус."""
    try:
        sheet = get_sheet()
        expected_headers = ["Текст", "Дата і час", "Оригінальне посилання", "Прямий лінк", "Статус"]
        rows = sheet.get_all_records(expected_headers=expected_headers)

        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)

        for idx, row in enumerate(rows, start=2):  # 2 — бо 1-й рядок це заголовки
            status = (row.get("Статус") or "").strip()
            dt_str = (row.get("Дата і час") or "").strip()
            text = (row.get("Текст") or "").strip()
            media_url = (row.get("Прямий лінк") or "").strip()

            if not status and dt_str and text:
                try:
                    dt = tz.localize(datetime.strptime(dt_str, "%Y-%m-%d %H:%M"))
                except ValueError:
                    logging.warning(f"Некоректна дата у рядку {idx}: {dt_str}")
                    continue

                if dt <= now:
                    footer = random.choice(FOOTERS)
                    final_text = f"{text}\n\n{footer}"
                    await send_to_channels(final_text, media_url)
                    sheet.update_cell(idx, 5, "✅")  # кол.5 = "Статус"
    except Exception as e:
        logging.error(f"Помилка в run_once: {e}")

# локальний ручний запуск однієї ітерації (не використовується на Render)
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_once())
