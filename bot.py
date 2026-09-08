"""Telegram launcher for the Mini App.

Run after installing requirements and setting BOT_TOKEN + WEB_APP_URL.
The bot does not contain secrets; Telegram Stars are confirmed server-side
in the successful_payment handler before a subscription is activated.
"""
from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    BotCommand,
    WebAppInfo,
)

router = Router()
WEB_APP_URL = os.environ["WEB_APP_URL"]
MONTHLY_STARS = int(os.getenv("MONTHLY_STARS", "300"))
APP_API_URL = os.getenv("APP_API_URL", "http://127.0.0.1:8000")
ADMIN_TELEGRAM_IDS = {
    value.strip() for value in (
        os.getenv("ADMIN_TELEGRAM_ID", "") + "," + os.getenv("ADMIN_TELEGRAM_IDS", "")
    ).split(",") if value.strip()
}


def app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть Astro App ✦", web_app=WebAppInfo(url=WEB_APP_URL))
    ]])


async def register_bot_user(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    payload = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language_code": user.language_code,
    }
    request = urllib.request.Request(
        f"{APP_API_URL}/api/register-user",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Bot-Token": os.environ.get("BOT_TOKEN", "")},
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except (OSError, ValueError):
        # Registration must not prevent the bot from answering the user.
        pass


@router.message(CommandStart())
async def start(message: Message) -> None:
    await register_bot_user(message)
    await message.answer(
        "Добро пожаловать в Astro App ✦\n"
        "Постройте карту рождения, изучите числа и получите подсказки для саморефлексии.",
        reply_markup=app_keyboard(),
    )


@router.message(Command("admin"))
async def admin(message: Message) -> None:
    await register_bot_user(message)
    if not ADMIN_TELEGRAM_IDS or str(message.from_user.id) not in ADMIN_TELEGRAM_IDS:
        await message.answer("Доступ запрещён.")
        return
    await message.answer("Админ-панель Astro App:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть админ-панель", web_app=WebAppInfo(url=f"{WEB_APP_URL.rstrip('/')}/admin"))
    ]]))


@router.message(F.text == "/subscribe")
async def subscribe(message: Message, bot: Bot) -> None:
    await register_bot_user(message)
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Astro App · месяц",
        description="Персональные прогнозы, совместимость и ежедневные подсказки.",
        payload=f"subscription:monthly:{message.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Месячная подписка", amount=MONTHLY_STARS)],
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    valid = query.invoice_payload.startswith("subscription:monthly:")
    await query.answer(ok=valid, error_message=None if valid else "Некорректный счёт")


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    payment = message.successful_payment
    payload = {
        "userId": str(message.from_user.id),
        "plan": "monthly",
        "telegramPaymentChargeId": payment.telegram_payment_charge_id,
    }
    request = urllib.request.Request(
        f"{APP_API_URL}/api/subscribe",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10):
        pass
    await message.answer(
        "Оплата получена ✦\n"
        "Подписка активирована. Вернитесь в приложение для доступа к отчётам.",
        reply_markup=app_keyboard(),
    )


async def configure_bot(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Открыть Astro App"),
        BotCommand(command="subscribe", description="Оформить подписку Stars"),
        BotCommand(command="admin", description="Админ-панель"),
    ])
    await bot.set_chat_menu_button(menu_button={"type": "web_app", "text": "Astro App", "web_app": WebAppInfo(url=WEB_APP_URL)})


async def notification_loop(bot: Bot) -> None:
    while True:
        try:
            if os.path.exists("astro_data.json"):
                data = json.loads(open("astro_data.json", encoding="utf-8").read())
                for user in data.get("users", {}).values():
                    subscription = user.get("subscription") or {}
                    telegram_id = user.get("telegramId")
                    if telegram_id and subscription.get("status") == "active":
                        card = {"name": "Карта дня"}
                        try:
                            with urllib.request.urlopen(f"{APP_API_URL}/api/tarot/card-of-day?userId={telegram_id}", timeout=10) as response:
                                card = json.loads(response.read()).get("card", card)
                        except (OSError, ValueError, KeyError):
                            pass
                        await bot.send_message(telegram_id, f"✦ Карта дня: {card['name']}\n{card.get('shortUpright', 'Откройте приложение для подробностей.')}", reply_markup=app_keyboard())
        except Exception:
            pass
        await asyncio.sleep(86400)


async def main() -> None:
    bot = Bot(os.environ["BOT_TOKEN"])
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    try:
        await configure_bot(bot)
    except TelegramNetworkError:
        # Polling has its own retry loop; menu configuration is also performed by the launcher.
        pass
    asyncio.create_task(notification_loop(bot))
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
