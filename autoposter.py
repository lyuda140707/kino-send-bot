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
import jsonload_dotenv()
import traceback
load_dotenv()
# ✅ разовий лог-чек середовища (побачиш у Render logs)
logging.warning(
    "ENV CHECK: B64=%d, JSON=%d, SHEET_ID=%s, BOT=%s",
    len((os.getenv("GOOGLE_SHEETS_CREDENTIALS_B64") or "").strip()),
    len((os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON") or "").strip()),
    ((os.getenv("SHEET_ID") or "")[:6] + "...") if os.getenv("SHEET_ID") else "MISSING",
    ("OK" if os.getenv("BOT_TOKEN") else "MISSING"),
)


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
    import base64, json

    # Достатній scope для Sheets + Drive
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    raw_b64 = (os.getenv("GOOGLE_SHEETS_CREDENTIALS_B64") or "").strip()
    if not raw_b64:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS_B64 is empty or not set")

    try:
        # прибираємо всі пробіли/перенесення на випадок, якщо вони є
        b64 = "".join(raw_b64.split())
        payload = base64.b64decode(b64).decode("utf-8")
        data = json.loads(payload)
    except Exception:
        logging.exception("Failed to decode/parse GOOGLE_SHEETS_CREDENTIALS_B64")
        raise

    email = data.get("client_email", "")
    logging.warning("CREDS OK: client_email=***%s", email[-18:] if email else "missing")

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
        logging.exception("Помилка в run_once")

# локальний ручний запуск однієї ітерації (не використовується на Render)
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_once())
