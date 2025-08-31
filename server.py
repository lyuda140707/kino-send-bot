# server.py
import os
import asyncio
import logging
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from autoposter import run_once, bot  # імпортуємо твою функцію з autoposter.py

app = FastAPI()

@app.get("/ping")
async def ping():
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    logging.basicConfig(level=logging.INFO)
    interval_min = int(os.getenv("POST_INTERVAL_MIN", "10"))  # кожні N хв перевіряти таблицю
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(run_once, IntervalTrigger(minutes=interval_min))
    scheduler.start()

    # одразу виконати одну ітерацію після старту
    asyncio.create_task(run_once())

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await bot.session.close()
    except Exception:
        pass
