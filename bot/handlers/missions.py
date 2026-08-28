from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, and_
from datetime import datetime
from database.db import get_db
from database.models import User, Mission, MissionCompletion, PointsHistory

async def missions_cmd(msg: types.Message):
    """Показать список миссий и прогресс пользователя"""
    async for session in get_db():
        user = await session.get(User, msg.from_user.id)
        if not user:
            await msg.answer("Сначала зарегистрируйся через /start")
            return

        missions = (await session.execute(
            select(Mission).where(Mission.is_active == True)
        )).scalars().all()

        text = "📋 <b>Твои миссии</b>\n\n"
        kb = InlineKeyboardMarkup(row_width=1)

        for mission in missions:
            completion = await session.scalar(
                select(MissionCompletion).where(
                    and_(
                        MissionCompletion.user_id == user.id,
                        MissionCompletion.mission_id == mission.id
                    )
                )
            )
            progress = completion.progress if completion else 0
            completed = completion.completed if completion else False

            status = "✅ Выполнено" if completed else f"📊 {progress}/{mission.required_count}"
            text += f"<b>{mission.name}</b>\n{mission.description}\nСтатус: {status}\n"
            if not completed:
                text += f"Награда: {mission.reward_points} баллов, {mission.reward_coins} монет\n\n"
            else:
                text += "\n"

            if not completed:
                kb.add(InlineKeyboardButton(
                    f"🔍 {mission.name}",
                    callback_data=f"mission_{mission.id}"
                ))

        if not missions:
            text = "🎯 Пока нет активных миссий."

        kb.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile"))
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")

async def missions_callback(call: types.CallbackQuery):
    """Обработка кнопки Миссии из меню"""
    await missions_cmd(call.message)
    await call.answer()

async def process_mission_action(call: types.CallbackQuery):
    """Выполнение шага миссии (имитация)"""
    mission_id = int(call.data.split("_")[1])

    async for session in get_db():
        user = await session.get(User, call.from_user.id)
        mission = await session.get(Mission, mission_id)

        if not mission or not mission.is_active:
            await call.answer("Миссия недоступна", show_alert=True)
            return

        completion = await session.scalar(
            select(MissionCompletion).where(
                and_(
                    MissionCompletion.user_id == user.id,
                    MissionCompletion.mission_id == mission_id
                )
            )
        )

        if not completion:
            completion = MissionCompletion(
                user_id=user.id,
                mission_id=mission_id,
                progress=0
            )
            session.add(completion)

        if completion.completed:
            await call.answer("Миссия уже выполнена", show_alert=True)
            return

        completion.progress += 1

        if completion.progress >= mission.required_count:
            completion.completed = True
            completion.completed_at = datetime.now()
            user.points += mission.reward_points
            user.coins += mission.reward_coins
            session.add(PointsHistory(
                user_id=user.id,
                points=mission.reward_points,
                reason=f"Миссия: {mission.name}"
            ))
            await call.answer(f"🎉 Миссия выполнена! +{mission.reward_points} баллов, +{mission.reward_coins} монет", show_alert=True)
        else:
            await call.answer(f"Прогресс: {completion.progress}/{mission.required_count}", show_alert=True)

        await session.commit()

    await missions_cmd(call.message)

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(missions_cmd, Command("missions"))
    dp.register_callback_query_handler(missions_callback, text="missions")
    dp.register_callback_query_handler(process_mission_action, lambda c: c.data.startswith("mission_"))
