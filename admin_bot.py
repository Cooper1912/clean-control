import asyncio
import httpx
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import Command

# ================= CONFIG =================

BOT_TOKEN = "8414415084:AAHJfqYcMWd6_5EoGDJHXf2jpo52Lve-cv4"
API_BASE = "https://clean-control.onrender.com"
ADMIN_ID = 8176375746   # твой telegram user_id

# ==========================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ================= START ==================

@router.message(Command("approve"))
async def approve_cleaner(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    uid = message.text.replace("/approve", "").strip()
    if not uid.isdigit():
        await message.answer("Использование: /approve <user_id>")
        return

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_BASE}/admin/approve_cleaner",
            json={"user_id": int(uid)}
        )

    await message.answer(f"✅ Клинер {uid} одобрен")

@router.message(Command("reject"))
async def reject_cleaner(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    uid = message.text.replace("/reject", "").strip()
    if not uid.isdigit():
        await message.answer("Использование: /reject <user_id>")
        return

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_BASE}/admin/reject_cleaner",
            json={"user_id": int(uid)}
        )

    await message.answer(f"❌ Клинер {uid} отклонён")

@router.message(Command("start"))
async def start(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Нет доступа")
        return

    await message.answer(
        "👑 Админ панель Clean Control\n\n"
        "/orders — 📦 активные заказы\n"
        "/cleaners — 👷 клинеры"
    )

# ================= ORDERS ==================

@router.message(Command("orders"))
async def list_orders(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{API_BASE}/admin/orders")

    orders = r.json()

    if not orders:
        await message.answer("Нет активных заказов")
        return

    for o in orders:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"cancel:{o['id']}"
                ),
                InlineKeyboardButton(
                    text="🔄 Снять с клинера",
                    callback_data=f"unassign:{o['id']}"
                )
            ]
        ])

        await message.answer(
            f"🧹 Заказ #{o['id']}\n"
            f"Статус: {o['status']}\n"
            f"Клинер: {o.get('cleaner_id') or '—'}\n"
            f"Цена: {o['price']} ₽",
            reply_markup=kb
        )

# ================= CALLBACKS ==================

@router.callback_query(F.data.startswith("cancel:"))
async def cancel_order(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return

    order_id = int(cb.data.split(":")[1])

    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.post(
            f"{API_BASE}/admin/cancel_order",
            json={
                "order_id": order_id,
                "reason": "Отменено администратором"
            }
        )

    if r.json().get("ok"):
        await cb.message.edit_text(
            f"❌ Заказ #{order_id} отменён администратором"
        )
    else:
        await cb.answer("Ошибка отмены", show_alert=True)

@router.callback_query(F.data.startswith("unassign:"))
async def unassign_order(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return

    order_id = int(cb.data.split(":")[1])

    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.post(
            f"{API_BASE}/admin/unassign_order",
            json={"order_id": order_id}
        )

    if r.json().get("ok"):
        await cb.message.edit_text(
            f"🔄 Заказ #{order_id} снят с клинера"
        )
    else:
        await cb.answer("Ошибка", show_alert=True)

# ================= CLEANERS ==================

@router.message(Command("cleaners"))
async def list_cleaners(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{API_BASE}/admin/cleaners")

    cleaners = r.json()

    if not cleaners:
        await message.answer("Клинеров нет")
        return

    for c in cleaners:
        await message.answer(
            f"{c['id']} — {c['name']} — {c['status']}"
        )

# ================= MAIN ==================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


    