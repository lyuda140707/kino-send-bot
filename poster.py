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

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    raw_b64 = (os.getenv("GOOGLE_SHEETS_CREDENTIALS_B64") or "").strip()
    if not raw_b64:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS_B64 is empty or not set")

    try:
        b64 = "".join(raw_b64.split())  # прибрати перенесення/пробіли всередині
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
        if not media_url:
            await bot.send_message(chat_id=channel, text=final_text)
            continue

        mu = media_url.lower().replace(".webb", ".webp")  # автофікс описки

        if mu.startswith(("baac", "bqac", "caac")):
            await bot.send_video(chat_id=channel, video=mu, caption=final_text)
        elif mu.endswith((".jpg", ".jpeg", ".png", ".webp")):
            await bot.send_photo(chat_id=channel, photo=mu, caption=final_text)
        elif mu.endswith((".mp4", ".mov", ".mkv", ".webm")):
            await bot.send_video(chat_id=channel, video=mu, caption=final_text)
        else:
            await bot.send_message(chat_id=channel, text=final_text)


async def run_once():
    """Одна ітерація: знайти пости на час і відправити їх, оновити статус."""
    try:
        sheet = get_sheet()

        # швидка перевірка доступу та заголовків
        try:
            a1 = sheet.acell("A1").value
            logging.warning("CHECK A1: %r", a1)
        except Exception:
            logging.exception("Не можу прочитати A1 — перевір SHEET_ID і доступ (Share: Editor на client_email)")
            return

        headers = sheet.row_values(1)
        logging.warning("HEADERS row1: %s", headers)

        # без expected_headers — сумісно з gspread 6.x
        rows = sheet.get_all_records()  # head=1 за замовчуванням

        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)

        def getv(row, key):
            return (row.get(key) or row.get(key.strip()) or "").strip()

        for idx, row in enumerate(rows, start=2):  # 2 — бо 1-й рядок це заголовки
            status    = getv(row, "Статус")
            dt_str    = getv(row, "Дата і час")
            text      = getv(row, "Текст")
            media_url = getv(row, "Прямий лінк")

            if status or not dt_str or not text:
                continue

            # парсимо дату у кількох форматах
            dt = None
            for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%Y/%m/%d %H:%M"):
                try:
                    naive = datetime.strptime(dt_str, fmt)
                    dt = tz.localize(naive)
                    break
                except ValueError:
                    continue

            if dt is None:
                logging.warning("Некоректна дата у рядку %d: %r", idx, dt_str)
                continue

            # ✅ ВАЖЛИВО: цей блок МАЄ бути всередині циклу for (з відступом)
            if dt <= now:
                footer = random.choice(FOOTERS)
                final_text = f"{text}\n\n{footer}"
                try:
                    # 1) тимчасова позначка, щоб не задублювати при рестарті
                    sheet.update_cell(idx, 5, "⏳")  # кол.5 = "Статус"

                    # 2) відправляємо
                    await send_to_channels(final_text, media_url)

                    # 3) фіксуємо успіх
                    sheet.update_cell(idx, 5, "✅")
                    logging.info("Відправлено рядок %d", idx)

                except Exception:
                    # 4) якщо збій — очистити статус, щоб спробувати ще
                    logging.exception("Збій під час відправки/оновлення для рядка %d", idx)
                    sheet.update_cell(idx, 5, "")
                    continue

    except Exception:
        logging.exception("Помилка в run_once")

async def close_bot():
    try:
        await bot.session.close()
    except Exception:
        logging.exception("Bot close failed")
