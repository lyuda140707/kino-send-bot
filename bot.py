import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F
import asyncio
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(F.video)
async def handle_video(msg: Message):
    file_id = msg.video.file_id
    await msg.reply(f"🎥 Video file_id:\n<code>{file_id}</code>")

@dp.message(F.photo)
async def handle_photo(msg: Message):
    file_id = msg.photo[-1].file_id
    await msg.reply(f"🖼 Photo file_id:\n<code>{file_id}</code>")

@dp.message(F.document)
async def handle_doc(msg: Message):
    file_id = msg.document.file_id
    await msg.reply(f"📄 Document file_id:\n<code>{file_id}</code>")

@dp.message()
async def handle_text(msg: Message):
    await msg.reply("👋 Надішли фото, відео або файл — я поверну <code>file_id</code>")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
