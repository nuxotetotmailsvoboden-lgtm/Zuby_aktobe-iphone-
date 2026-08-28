from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from sqlalchemy import select
from database.db import get_db
from database.models import User, PointsHistory
from bot.config import ADMIN_IDS

async def insta_verify_request(msg: types.Message):
    """Пользователь запрашивает проверку подписки на Instagram"""
    async for session in get_db():
        user = await session.get(User, msg.from_user.id)
        if not user:
            await msg.answer("Сначала зарегистрируйся через /start")
            return
        if not user.instagram:
            await msg.answer("Ты не указал Instagram. Заполни анкету заново через /start")
            return
        if user.instagram_subscribed:
            await msg.answer("✅ Твоя подписка уже подтверждена!")
            return

        # Отправляем запрос админам
        for admin_id in ADMIN_IDS:
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"insta_approve_{user.id}"),
                types.InlineKeyboardButton("❌ Отклонить", callback_data=f"insta_reject_{user.id}")
            )
            await msg.bot.send_message(
                admin_id,
                f"🔔 Запрос на проверку Instagram\n"
                f"👤 {user.full_name} (@{user.username})\n"
                f"📷 Ник: {user.instagram}",
                reply_markup=kb
            )

        await msg.answer("📨 Запрос отправлен администратору. Ожидай подтверждения.")

async def admin_insta_action(call: types.CallbackQuery):
    """Админ одобряет или отклоняет подписку"""
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return

    data = call.data.split("_")
    action = data[1]
    user_id = int(data[2])

    async for session in get_db():
        user = await session.get(User, user_id)
        if not user:
            await call.answer("Пользователь не найден", show_alert=True)
            return

        if action == "approve":
            if user.instagram_subscribed:
                await call.answer("Уже подтверждено", show_alert=True)
                return
            user.instagram_subscribed = True
            user.points += 50
            session.add(PointsHistory(user_id=user.id, points=50, reason="Подписка на Instagram"))
            await session.commit()
            await call.message.edit_text(call.message.text + "\n\n✅ Подтверждено")
            try:
                await call.bot.send_message(user_id, "🎉 Твоя подписка на Instagram подтверждена! +50 баллов.")
            except:
                pass
            await call.answer("Подтверждено")
        else:
            await call.message.edit_text(call.message.text + "\n\n❌ Отклонено")
            try:
                await call.bot.send_message(user_id, "❌ Подписка на Instagram не подтверждена.")
            except:
                pass
            await call.answer("Отклонено")

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(insta_verify_request, Command("verify_insta"))
    dp.register_callback_query_handler(admin_insta_action, lambda c: c.data.startswith("insta_"))
