import os
import logging
import asyncio
from datetime import datetime
import pytz
from aiogram.client.default import DefaultBotProperties

from aiogram import Bot
from aiogram.enums import ParseMode

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

# Налаштування
BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
CHANNEL_USERNAMES = ["@KinoTochkaUA", "@KinoTochkaFilms"]
TIMEZONE = "Europe/Kyiv"

# Підключення до бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Google Sheets авторизація
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_data = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(creds_data), scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

async def check_and_post():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Відкрити WebApp", url="https://t.me/UAKinoTochka_bot")]
    ])
    
    while True:
        try:
            sheet = get_sheet()
            rows = sheet.get_all_records()
            for idx, row in enumerate(rows, start=2):
                status = row.get("E (Статус)", "")
                dt_str = row.get("B (Дата і час)", "")
                text = row.get("A (Текст)", "")
                media_url = row.get("D — Прямий лінк (формула)", "")

                if not status and dt_str and text:
                    tz = pytz.timezone(TIMEZONE)
                    dt = tz.localize(datetime.strptime(dt_str, "%Y-%m-%d %H:%M"))
                    now = datetime.now(tz)

                    if dt <= now:
                        final_text = f"{text}\n\n🔎 <b>Шукай фільм у WebApp!</b>"

                        for channel in CHANNEL_USERNAMES:
                            if media_url.startswith(("BAAC", "BQAC", "CAAC")):
                                await bot.send_video(chat_id=channel, video=media_url, caption=final_text, reply_markup=keyboard)
                            elif media_url.endswith((".jpg", ".jpeg", ".png", ".webp")):
                                await bot.send_photo(chat_id=channel, photo=media_url, caption=final_text, reply_markup=keyboard)
                            elif media_url.endswith((".mp4", ".mov", ".mkv")):
                                await bot.send_video(chat_id=channel, video=media_url, caption=final_text, reply_markup=keyboard)
                            else:
                                await bot.send_message(chat_id=channel, text=final_text, reply_markup=keyboard)

                      


                        # Позначити як опубліковане
                        sheet.update_cell(idx, 5, "✅")

        except Exception as e:
            logging.error(f"Помилка: {e}")

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(check_and_post())
