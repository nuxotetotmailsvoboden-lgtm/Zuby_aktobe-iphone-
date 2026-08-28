import random
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
import logging

from db.base import async_session
from db.models import Raffle, RaffleParticipant, User, Referral
from sqlalchemy import select
from keyboards.raffle import get_raffle_keyboard
from keyboards.main_menu import get_back_keyboard
from services.antifraud import AntiFraudService

logger = logging.getLogger(__name__)
router = Router(name="raffle")


@router.callback_query(F.data.startswith("raffle_join_"))
async def join_raffle(callback: CallbackQuery):
    """Участвовать в розыгрыше"""
    await callback.answer()
    
    raffle_id = int(callback.data.replace("raffle_join_", ""))
    telegram_id = callback.from_user.id
    
    async with async_session() as session:
        raffle_result = await session.execute(
            select(Raffle).where(Raffle.id == raffle_id, Raffle.status == "active")
        )
        raffle = raffle_result.scalar_one_or_none()
        
        if not raffle:
            await callback.answer("Розыгрыш не найден или завершён", show_alert=True)
            return
        
        participant_result = await session.execute(
            select(RaffleParticipant).where(
                RaffleParticipant.raffle_id == raffle_id,
                RaffleParticipant.user_id == telegram_id,
            )
        )
        if participant_result.scalar_one_or_none():
            await callback.answer("Вы уже участвуете в этом розыгрыше!", show_alert=True)
            return
        
        weight = await calculate_weight(telegram_id, session)
        
        fraud_mult = await AntiFraudService.get_multiplier(telegram_id)
        if fraud_mult < 0.5:
            weight *= 0.1
        
        participant = RaffleParticipant(
            raffle_id=raffle_id,
            user_id=telegram_id,
            weight=weight,
        )
        session.add(participant)
        await session.commit()
    
    await callback.message.edit_text(
        f"🎉 <b>ВЫ УЧАСТВУЕТЕ!</b>\n\n"
        f"🏆 Приз: <b>{raffle.prize_name}</b>\n"
        f"📊 Ваш вес: <b>{weight:.2f}</b>\n\n"
        f"Чем больше вес — тем выше шанс победить!\n\n"
        f"📈 <b>Как увеличить вес:</b>\n"
        f"• Приглашайте друзей (+1.5 за каждого)\n"
        f"• Посещайте клинику (+3 за визит)\n"
        f"• Чем больше сумма чеков, тем выше вес\n\n"
        f"Результаты будут объявлены после завершения розыгрыша!",
        parse_mode="HTML",
        reply_markup=get_back_keyboard("menu_raffle")
    )


@router.callback_query(F.data == "raffle_chances")
async def show_raffle_chances(callback: CallbackQuery):
    """Показать шансы в розыгрышах"""
    await callback.answer()
    
    telegram_id = callback.from_user.id
    
    async with async_session() as session:
        participations = await session.execute(
            select(RaffleParticipant, Raffle)
            .join(Raffle)
            .where(
                RaffleParticipant.user_id == telegram_id,
                Raffle.status == "active",
            )
        )
        results = participations.all()
        
        if not results:
            await callback.message.edit_text(
                "📊 <b>МОИ ШАНСЫ</b>\n\n"
                "<i>Вы пока не участвуете ни в одном розыгрыше.</i>\n\n"
                "Присоединяйтесь к активным розыгрышам!",
                parse_mode="HTML",
                reply_markup=get_back_keyboard("menu_raffle")
            )
            return
        
        text = "📊 <b>МОИ ШАНСЫ В РОЗЫГРЫШАХ</b>\n\n"
        
        for participation, raffle in results:
            total_result = await session.execute(
                select(RaffleParticipant).where(
                    RaffleParticipant.raffle_id == raffle.id
                )
            )
            all_participants = total_result.scalars().all()
            total_weight = sum(p.weight for p in all_participants)
            
            chance = (participation.weight / total_weight * 100) if total_weight > 0 else 0
            
            text += (
                f"🏆 <b>{raffle.prize_name}</b>\n"
                f"📊 Ваш вес: {participation.weight:.2f}\n"
                f"👥 Участников: {len(all_participants)}\n"
                f"🎯 Шанс: <b>{chance:.2f}%</b>\n\n"
            )
        
        text += "<i>Шансы обновляются в реальном времени</i>"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard("menu_raffle")
    )


async def calculate_weight(telegram_id: int, session) -> float:
    """Рассчитать вес пользователя для розыгрыша"""
    user_result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        return 1.0
    
    refs_result = await session.execute(
        select(Referral).where(Referral.referrer_id == user.id)
    )
    refs = refs_result.scalars().all()
    
    weight = (
        (len(refs) * 1.5) +
        (user.total_visits * 3) +
        (user.total_checks / 1000)
    )
    
    return max(weight, 1.0)


@router.callback_query(F.data == "raffle_draw_test")
async def test_draw_winner(callback: CallbackQuery):
    """Тестовый розыгрыш (только для админов)"""
    await callback.answer()
    
    from config import settings
    if callback.from_user.id not in settings.SUPERADMINS:
        await callback.answer("Только для суперадминов", show_alert=True)
        return
    
    async with async_session() as session:
        raffle_result = await session.execute(
            select(Raffle).where(Raffle.status == "active")
        )
        raffle = raffle_result.scalar_one_or_none()
        
        if not raffle:
            await callback.message.edit_text(
                "Нет активных розыгрышей",
                reply_markup=get_back_keyboard("menu_raffle")
            )
            return
        
        participants_result = await session.execute(
            select(RaffleParticipant).where(RaffleParticipant.raffle_id == raffle.id)
        )
        participants = participants_result.scalars().all()
        
        if not participants:
            await callback.message.edit_text(
                "Нет участников в розыгрыше",
                reply_markup=get_back_keyboard("menu_raffle")
            )
            return
        
        weights = [p.weight for p in participants]
        winner = random.choices(participants, weights=weights, k=1)[0]
        
        raffle.status = "completed"
        raffle.winner_id = winner.user_id
        raffle.completed_at = datetime.utcnow()
        await session.commit()
        
        winner_user = await session.execute(
            select(User).where(User.telegram_id == winner.user_id)
        )
        winner_user = winner_user.scalar_one_or_none()
    
    await callback.message.edit_text(
        f"🎉 <b>РОЗЫГРЫШ ЗАВЕРШЁН!</b>\n\n"
        f"🏆 Приз: <b>{raffle.prize_name}</b>\n"
        f"👤 Победитель: {winner_user.first_name} {winner_user.last_name}\n"
        f"📊 Вес победителя: {winner.weight:.2f}\n"
        f"👥 Всего участников: {len(participants)}",
        parse_mode="HTML",
        reply_markup=get_back_keyboard("menu_raffle")
    )
    
    try:
        await callback.bot.send_message(
            winner.user_id,
            f"🎉 <b>ПОЗДРАВЛЯЕМ!</b>\n\n"
            f"Вы выиграли в розыгрыше!\n"
            f"🏆 Приз: <b>{raffle.prize_name}</b>\n\n"
            f"С вами свяжется администратор для вручения приза!",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить победителя: {e}")
