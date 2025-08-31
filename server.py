# server.py
import os
import asyncio
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# імпортуй з твого скрипта функцію, яка робить одну “ітерацію” посту
# (див. приклад нижче у п.1.2)
from autoposter import run_once

app = FastAPI()

@app.get("/ping")
async def ping():
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    # ПЛАНУВАЛЬНИК: запускаємо run_once кожні N хв
    interval_min = int(os.getenv("POST_INTERVAL_MIN", "10"))
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(run_once, IntervalTrigger(minutes=interval_min))
    scheduler.start()

    # (опційно) — одразу одна спроба при старті:
    asyncio.create_task(run_once())
