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
logging.basicConfig(level=logging.INFO)

# Налаштування
BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TIMEZONE = "Europe/Kyiv"

# Підключення до бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Авторизація Google Sheets
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_data = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(creds_data), scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

# Головна функція автопостингу
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

                        try:
                            # Фото
                            if media_url.endswith((".jpg", ".jpeg", ".png", ".webp")):
                                await bot.send_photo(
                                    chat_id=CHANNEL_USERNAME,
                                    photo=media_url,
                                    caption=final_text,
                                    reply_markup=keyboard
                                )

                            # file_id з Telegram
                            elif media_url.startswith(("BAAC", "BQAC", "CAAC")):
                                try:
                                    await bot.send_video(
                                        chat_id=CHANNEL_USERNAME,
                                        video=media_url,
                                        caption=final_text,
                                        reply_markup=keyboard
                                    )
                                except Exception as inner_e:
                                    logging.warning(f"⚠️ Не вдалося як video, пробую як document: {inner_e}")
                                    await bot.send_document(
                                        chat_id=CHANNEL_USERNAME,
                                        document=media_url,
                                        caption=final_text,
                                        reply_markup=keyboard
                                    )

                            # mp4 або інші відео
                            else:
                                await bot.send_video(
                                    chat_id=CHANNEL_USERNAME,
                                    video=media_url,
                                    caption=final_text,
                                    reply_markup=keyboard
                                )

                            # ✅ Позначаємо як опубліковане
                            try:
                                cell_address = f"E{idx}"
                                sheet.update_acell(cell_address, "✅")
                                logging.info(f"✅ Статус оновлено в таблиці для рядка {idx}")
                            except Exception as update_err:
                                logging.error(f"❌ Не вдалося оновити статус у таблиці (рядок {idx}): {update_err}")

                        except Exception as e:
                            logging.error(f"❌ Не вдалося надіслати медіа: {e}")
                            await bot.send_message(chat_id=CHANNEL_USERNAME, text=final_text, reply_markup=keyboard)

        except Exception as e:
            logging.error(f"🔥 Загальна помилка: {e}")

        await asyncio.sleep(60)

# Запуск
if __name__ == "__main__":
    asyncio.run(check_and_post())
