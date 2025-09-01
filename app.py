import os
import asyncio
import logging
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import poster  # це твій файл вище, де є run_once()

app = FastAPI()
scheduler = AsyncIOScheduler()
@app.get("/")
async def root():
    return {"ok": True, "ping": "/ping"}


@app.get("/ping")
async def ping():
    return {"status": "ok"}

# (необов'язково) Кнопка “запустити зараз” для швидкої перевірки
@app.post("/run-now")
async def run_now():
    # запускаємо поза розкладом, не блокуємо відповідь
    asyncio.create_task(poster.run_once())
    return {"started": True}

@app.on_event("startup")
async def on_startup():
    logging.info("Starting scheduler...")
    # 🔁 ЗАПЛАНУЙ: раз на N хвилин (підбери свій інтервал)
    scheduler.add_job(poster.run_once, "interval", minutes=3, id="poster_job", max_instances=1, coalesce=True)
    scheduler.start()

    # ▶️ Запустити одразу один раз у фоні (не блокує старт)
    asyncio.create_task(poster.run_once())

@app.on_event("shutdown")
async def on_shutdown():
    logging.info("Shutting down scheduler...")
    try:
        scheduler.shutdown()
    except Exception:
        logging.exception("Scheduler shutdown failed")
    # акуратно закрити aiogram Bot
    await poster.close_bot()
