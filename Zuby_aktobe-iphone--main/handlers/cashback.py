from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PhotoSize, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
from datetime import datetime

from db.base import async_session
from db.models import User, Booking, Reward
from sqlalchemy import select
from services.discount import DiscountEngine
from services.antifraud import AntiFraudService
from services.booking_service import BookingService
from config import settings

logger = logging.getLogger(__name__)
router = Router(name="cashback")


# ──────────────────────────────────────
# FSM для отправки чека
# ──────────────────────────────────────
class CashbackFSM(StatesGroup):
    waiting_for_receipt = State()      # ожидаем фото/скан чека
    waiting_for_amount = State()       # уточняем сумму (если не видно)
    confirm_by_admin = State()         # ожидает подтверждения админом


# ──────────────────────────────────────
# ВХОД В РЕЖИМ "ОТПРАВКА ЧЕКА"
# ──────────────────────────────────────
@router.callback_query(F.data == "cashback_send_receipt")
async def start_cashback(callback: CallbackQuery, state: FSMContext):
    """Пользователь хочет отправить чек для начисления кэшбека"""
    await callback.answer()

    await callback.message.edit_text(
        "🧾 <b>КЭШБЕК ЗА ВИЗИТ</b>\n\n"
        "Сфотографируйте или отправьте скан чека из нашей клиники.\n\n"
        "<b>Требования:</b>\n"
        "• Чёткое фото всего чека\n"
        "• Видна дата и сумма\n"
        "• Чек должен быть из стоматологии\n\n"
        "<i>После проверки администратором вам начислят кэшбек-скидку.</i>\n\n"
        "📎 Отправьте фото или скан чека:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CashbackFSM.waiting_for_receipt)


# ──────────────────────────────────────
# ПОЛУЧЕНИЕ ЧЕКА
# ──────────────────────────────────────
@router.message(CashbackFSM.waiting_for_receipt, F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT}))
async def receive_receipt_photo(message: Message, state: FSMContext):
    """Получили фото или документ"""
    telegram_id = message.from_user.id

    if message.photo:
        # Берём самое большое фото
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.document:
        # Проверяем, что это изображение
        if not message.document.mime_type or not message.document.mime_type.startswith("image/"):
            await message.answer(
                "❌ Пожалуйста, отправьте <b>изображение</b> чека (фото или скан).\n"
                "PDF и другие форматы пока не поддерживаются.",
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard()
            )
            return
        file_id = message.document.file_id
        file_type = "document"
    else:
        await message.answer(
            "❌ Отправьте фото или скан чека.",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(
        receipt_file_id=file_id,
        receipt_file_type=file_type,
        receipt_message_id=message.message_id,
    )

    # Спрашиваем сумму чека (на случай если не видно)
    await message.answer(
        "📸 Чек получен!\n\n"
        "Для точности <b>введите сумму чека</b> (только число, например: <code>15000</code>):\n\n"
        "<i>Если не знаете точную сумму — напишите 0, администратор сверит сам.</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CashbackFSM.waiting_for_amount)


@router.message(CashbackFSM.waiting_for_receipt)
async def invalid_receipt_format(message: Message):
    """Неверный формат"""
    await message.answer(
        "❌ Отправьте <b>фото</b> или <b>скан</b> чека.\n"
        "Текстовые сообщения не принимаются.",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


# ──────────────────────────────────────
# ПОЛУЧЕНИЕ СУММЫ
# ──────────────────────────────────────
@router.message(CashbackFSM.waiting_for_amount)
async def receive_amount(message: Message, state: FSMContext):
    """Получили сумму чека"""
    try:
        amount_text = message.text.strip().replace(",", ".").replace(" ", "")
        amount = float(amount_text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Введите <b>число</b> (например: 15000 или 7500.50)",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()
    telegram_id = message.from_user.id

    # Проверяем пользователя
    async with async_session() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start")
        await state.clear()
        return

    # Отправляем на проверку администратору
    await notify_admins_about_receipt(
        bot=message.bot,
        user=user,
        file_id=data["receipt_file_id"],
        file_type=data["receipt_file_type"],
        amount=amount,
        state=state,
        chat_id=message.chat.id,
    )

    await message.answer(
        "✅ <b>ЧЕК ОТПРАВЛЕН НА ПРОВЕРКУ</b>\n\n"
        f"💰 Сумма: <b>{amount:,.2f} ₽</b>\n\n"
        "⏳ Администратор проверит чек в течение рабочего дня.\n"
        "После подтверждения вам будет начислен кэшбек.\n\n"
        "<i>Вы получите уведомление о результате.</i>",
        parse_mode="HTML",
        reply_markup=get_main_menu_inline()
    )

    await state.clear()


# ──────────────────────────────────────
# УВЕДОМЛЕНИЕ АДМИНАМ
# ──────────────────────────────────────
async def notify_admins_about_receipt(bot, user, file_id, file_type, amount, state: FSMContext, chat_id):
    """Отправляем админам чек на проверку"""
    from keyboards.admin import get_receipt_approve_keyboard

    # Формируем временный ID для связи (user_id + timestamp)
    receipt_id = f"{user.telegram_id}_{int(datetime.utcnow().timestamp())}"
    
    # Сохраняем receipt_id в состоянии для последующей обработки
    await state.update_data(receipt_id=receipt_id, receipt_amount=amount)

    admin_text = (
        f"🧾 <b>НОВЫЙ ЧЕК НА ПРОВЕРКУ</b>\n\n"
        f"👤 Пациент: {user.first_name} {user.last_name}\n"
        f"📱 Телефон: {user.phone}\n"
        f"🆔 Telegram ID: {user.telegram_id}\n"
        f"💰 Заявленная сумма: {amount:,.2f} ₽\n"
        f"👥 Визитов всего: {user.total_visits}\n"
        f"⭐ VIP: {'Да' if user.is_vip else 'Нет'}\n"
        f"🔑 ID чека: <code>{receipt_id}</code>\n\n"
        f"<b>Чек прикреплён ниже:</b>"
    )

    for admin_id in settings.SUPERADMINS + settings.ADMINS:
        try:
            if file_type == "photo":
                await bot.send_photo(
                    admin_id,
                    photo=file_id,
                    caption=admin_text,
                    parse_mode="HTML",
                    reply_markup=get_receipt_approve_keyboard(
                        user_id=user.telegram_id,
                        receipt_id=receipt_id,
                        amount=amount,
                    )
                )
            else:
                await bot.send_document(
                    admin_id,
                    document=file_id,
                    caption=admin_text,
                    parse_mode="HTML",
                    reply_markup=get_receipt_approve_keyboard(
                        user_id=user.telegram_id,
                        receipt_id=receipt_id,
                        amount=amount,
                    )
                )
        except Exception as e:
            logger.error(f"Не удалось отправить чек админу {admin_id}: {e}")


# ──────────────────────────────────────
# ПОДТВЕРЖДЕНИЕ / ОТКЛОНЕНИЕ АДМИНОМ
# ──────────────────────────────────────
@router.callback_query(F.data.startswith("receipt_approve_"))
async def approve_receipt(callback: CallbackQuery):
    """Админ одобрил чек → начисляем кэшбек"""
    await callback.answer()

    # Формат: receipt_approve_{user_id}_{receipt_id}_{amount}
    parts = callback.data.replace("receipt_approve_", "").split("_")
    user_id = int(parts[0])
    amount = float(parts[-1]) if len(parts) > 2 else 0.0

    # Определяем процент кэшбека
    async with async_session() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()

    if not user:
        try:
            await callback.message.edit_caption(
                caption=f"{callback.message.caption}\n\n❌ Пользователь не найден",
                parse_mode="HTML"
            )
        except:
            pass
        return

    if user.is_vip:
        cashback_percent = settings.CASHBACK_VIP_PERCENT
    elif amount >= 50000:
        cashback_percent = 7.0
    elif amount >= 20000:
        cashback_percent = 5.0
    else:
        cashback_percent = settings.CASHBACK_BASE_PERCENT

    # Начисляем кэшбек
    await DiscountEngine.add_discount(
        user_id=user_id,
        amount=cashback_percent,
        source="cashback",
    )

    # Обновляем общую сумму чеков пользователя
    async with async_session() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user_update = user_result.scalar_one_or_none()
        if user_update:
            user_update.total_checks += amount
            await session.commit()

    # Обновляем антифрод
    await AntiFraudService.update_score(user_id, "visit")

    # Обновляем сообщение админа
    new_caption = (
        f"{callback.message.caption or ''}\n\n"
        f"✅ <b>ОДОБРЕНО</b>\n"
        f"💰 Начислен кэшбек: <b>+{cashback_percent}%</b>\n"
        f"👤 Админ: {callback.from_user.full_name}"
    )

    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=new_caption, parse_mode="HTML")
        else:
            await callback.message.edit_text(new_caption, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения: {e}")

    # Уведомление пользователю
    try:
        await callback.bot.send_message(
            user_id,
            f"✅ <b>ЧЕК ПОДТВЕРЖДЁН!</b>\n\n"
            f"💰 Сумма чека: {amount:,.2f} ₽\n"
            f"🎁 Начислен кэшбек: <b>+{cashback_percent}%</b>\n\n"
            f"💎 Ваша скидка теперь доступна в разделе 🎁 Мои скидки\n\n"
            f"Спасибо, что выбираете нас! 🦷",
            parse_mode="HTML",
            reply_markup=get_main_menu_inline()
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")

    await callback.answer(f"✅ Кэшбек +{cashback_percent}% начислен!", show_alert=True)


@router.callback_query(F.data.startswith("receipt_reject_"))
async def reject_receipt(callback: CallbackQuery):
    """Админ отклонил чек"""
    await callback.answer()

    # Формат: receipt_reject_{user_id}_{receipt_id}
    # Берём только user_id (первый элемент после receipt_reject_)
    data_part = callback.data.replace("receipt_reject_", "")
    parts = data_part.split("_")
    user_id = int(parts[0])

    new_caption = (
        f"{callback.message.caption or ''}\n\n"
        f"❌ <b>ОТКЛОНЕНО</b>\n"
        f"👤 Админ: {callback.from_user.full_name}"
    )

    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=new_caption, parse_mode="HTML")
        else:
            await callback.message.edit_text(new_caption, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения: {e}")

    # Уведомление пользователю
    try:
        await callback.bot.send_message(
            user_id,
            "❌ <b>ЧЕК ОТКЛОНЁН</b>\n\n"
            "К сожалению, ваш чек не прошёл проверку.\n"
            "Возможные причины:\n"
            "• Чек не из нашей клиники\n"
            "• Неразборчивое фото\n"
            "• Чек уже был использован\n\n"
            "Вы можете отправить другой чек или обратиться к администратору.",
            parse_mode="HTML",
            reply_markup=get_main_menu_inline()
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")

    await callback.answer("❌ Чек отклонён", show_alert=True)


# ──────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ КЛАВИАТУРЫ
# ──────────────────────────────────────
def get_cancel_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cashback_cancel"))
    return builder.as_markup()


def get_main_menu_inline():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main"))
    return builder.as_markup()


@router.callback_query(F.data == "cashback_cancel")
async def cancel_cashback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "❌ Отправка чека отменена.",
        reply_markup=get_main_menu_inline()
    )
