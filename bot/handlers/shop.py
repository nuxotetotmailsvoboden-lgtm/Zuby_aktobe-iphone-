from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from database.db import get_db
from database.models import User, ShopItem, ShopPurchase, PointsHistory, LotteryEntry

async def shop_cmd(msg: types.Message):
    """Показать витрину магазина"""
    async for session in get_db():
        items = (await session.execute(
            select(ShopItem).where(ShopItem.is_active == True)
        )).scalars().all()

        if not items:
            await msg.answer("🛒 Магазин пока пуст.")
            return

        text = "🛍 <b>Магазин бонусов</b>\n\n"
        kb = InlineKeyboardMarkup(row_width=1)

        for item in items:
            cost_str = []
            if item.cost_coins:
                cost_str.append(f"{item.cost_coins} 🪙")
            if item.cost_points:
                cost_str.append(f"{item.cost_points} 🎯")
            cost = " / ".join(cost_str)
            text += f"<b>{item.name}</b> — {cost}\n{item.description}\n\n"
            kb.add(InlineKeyboardButton(
                f"🛒 {item.name}",
                callback_data=f"buy_{item.id}"
            ))

        kb.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile"))
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")

async def shop_callback(call: types.CallbackQuery):
    """Обработка нажатия на кнопку магазина из меню"""
    await shop_cmd(call.message)
    await call.answer()

async def buy_item(call: types.CallbackQuery):
    """Покупка товара"""
    item_id = int(call.data.split("_")[1])

    async for session in get_db():
        user = await session.get(User, call.from_user.id)
        item = await session.get(ShopItem, item_id)

        if not item or not item.is_active:
            await call.answer("Товар недоступен", show_alert=True)
            return

        if item.cost_points > 0 and user.points < item.cost_points:
            await call.answer("Недостаточно баллов", show_alert=True)
            return
        if item.cost_coins > 0 and user.coins < item.cost_coins:
            await call.answer("Недостаточно монет", show_alert=True)
            return

        # Списываем
        if item.cost_points:
            user.points -= item.cost_points
            session.add(PointsHistory(user_id=user.id, points=-item.cost_points, reason=f"Покупка: {item.name}"))
        if item.cost_coins:
            user.coins -= item.cost_coins

        purchase = ShopPurchase(user_id=user.id, item_id=item.id)
        session.add(purchase)

        # Применяем эффект товара
        if item.type == "ticket":
            # Ищем активный розыгрыш (id=1 для простоты, в реальности надо брать из БД)
            from database.models import Lottery
            lottery = await session.scalar(select(Lottery).where(Lottery.is_active == True).limit(1))
            if lottery:
                entry = await session.scalar(
                    select(LotteryEntry).where(
                        LotteryEntry.user_id == user.id,
                        LotteryEntry.lottery_id == lottery.id
                    )
                )
                if entry:
                    entry.tickets += 1
                else:
                    entry = LotteryEntry(user_id=user.id, lottery_id=lottery.id, tickets=1)
                    session.add(entry)
                await call.answer("Вы получили билет в розыгрыш!", show_alert=True)
        elif item.type == "points":
            bonus = item.effect.get("points", 0)
            user.points += bonus
            session.add(PointsHistory(user_id=user.id, points=bonus, reason=f"Товар: {item.name}"))

        await session.commit()
        await call.message.edit_text(f"✅ Вы приобрели {item.name}!")

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(shop_cmd, Command("shop"))
    dp.register_callback_query_handler(shop_callback, text="shop")
    dp.register_callback_query_handler(buy_item, lambda c: c.data.startswith("buy_"))
