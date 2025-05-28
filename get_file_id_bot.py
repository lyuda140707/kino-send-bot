import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")  # той самий, що в autoposter
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(lambda msg: msg.video or msg.document)
async def handle_file_id(msg: types.Message):
    if msg.video:
        await msg.reply(f"🎬 Відео file_id:\n<code>{msg.video.file_id}</code>")
    elif msg.document:
        await msg.reply(f"📎 Документ file_id:\n<code>{msg.document.file_id}</code>")

@dp.message()
async def catch_all(msg: types.Message):
    await msg.reply("⬆️ Надішли відео або файл, і я пришлю тобі file_id")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
