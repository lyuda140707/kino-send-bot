import os
import asyncio
import logging
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.responses import PlainTextResponse
from fastapi import Request

import poster  # це твій файл вище, де є run_once()

app = FastAPI()
scheduler = AsyncIOScheduler()

@app.api_route("/", methods=["GET", "HEAD"])
async def root(request: Request):
    # Render шле HEAD / — відповідаємо 200 без тіла
    if request.method == "HEAD":
        return PlainTextResponse("", status_code=200)
    # GET /
    return {"ok": True, "ping": "/ping"}



@app.get("/ping")
async def ping():
    return {"status": "ok"}


# (необов'язково) Кнопка “запустити зараз” для швидкої перевірки
@app.api_route("/run-now", methods=["GET", "POST"])
async def run_now():
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
