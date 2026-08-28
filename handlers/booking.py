from datetime import date, time, datetime, timedelta
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
import logging

from states.fsm import BookingFSM
from keyboards.booking import (
    SERVICES,
    SERVICE_DURATIONS,
    get_booking_services_keyboard,
    get_date_keyboard,
    get_time_keyboard,
    get_confirm_keyboard,
    get_booking_success_keyboard,
    get_alternative_keyboard,
)
from keyboards.main_menu import get_back_keyboard, get_main_menu_keyboard
from services.booking_service import BookingService, SlotBusyException
from services.discount import DiscountEngine
from services.antifraud import AntiFraudService

logger = logging.getLogger(__name__)
router = Router(name="booking")


def _to_date(val):
    """Конвертирует строку ISO в date, если нужно"""
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return datetime.strptime(val, '%Y-%m-%d').date()
        except:
            return None
    return val


def _to_time(val):
    """Конвертирует строку HH:MM в time, если нужно"""
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        try:
            h, m = map(int, val.split(':'))
            return time(h, m)
        except:
            return None
    return val


@router.callback_query(F.data.startswith("service_"))
async def process_service_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    service_key = callback.data
    service_duration = SERVICE_DURATIONS.get(service_key, 60)
    service_name = 'Услуга'
    for name, key in SERVICES:
        if key == service_key:
            service_name = name
            break

    await state.update_data(service=service_name, service_key=service_key, service_duration=service_duration)
    available_dates = await BookingService.get_available_dates(service_duration)

    if not available_dates:
        await callback.message.edit_text(
            f'📅 <b>{service_name}</b>\n\n'
            f'❌ На ближайшие {BookingService.MAX_DAYS_AHEAD} дней нет свободных слотов.\n\n'
            f'Попробуйте выбрать другую услугу или обратитесь к администратору.',
            parse_mode='HTML',
            reply_markup=get_booking_services_keyboard()
        )
        return

    await callback.message.edit_text(
        f'📅 <b>{service_name}</b>\n'
        f'⏱ Длительность: <b>{service_duration} мин</b>\n\n'
        f'<b>Выберите дату:</b>',
        parse_mode='HTML',
        reply_markup=get_date_keyboard(available_dates, service_duration)
    )
    await state.set_state(BookingFSM.date)


@router.callback_query(BookingFSM.date, F.data.startswith("date_"))
async def process_date_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    date_str = callback.data.replace('date_', '')
    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    data = await state.get_data()
    service_duration = data.get('service_duration', 60)

    logger.info(f"Выбрана дата: {selected_date}, длительность: {service_duration}")
    available_slots = await BookingService.get_available_slots(selected_date, service_duration)
    logger.info(f"Доступные слоты: {available_slots}")

    if not available_slots:
        alt_result = await BookingService.find_nearest_available(selected_date, time(9, 0), service_duration)
        # Сохраняем как строку!
        await state.update_data(selected_date=selected_date.isoformat())
        await callback.message.edit_text(
            f'📅 <b>{selected_date.strftime("%d.%m.%Y")}</b>\n\n'
            f'❌ На эту дату все слоты заняты.\n\n',
            parse_mode='HTML',
            reply_markup=get_alternative_keyboard(alt_result) if alt_result else get_booking_services_keyboard()
        )
        return

    # Сохраняем как строку!
    await state.update_data(selected_date=selected_date.isoformat())
    await callback.message.edit_text(
        f'📅 <b>{selected_date.strftime("%d.%m.%Y")}</b>\n'
        f'🦷 {data.get("service", "Услуга")}\n\n'
        f'<b>Доступное время:</b>\n\n'
        f'Выберите удобное время:',
        parse_mode='HTML',
        reply_markup=get_time_keyboard(available_slots, selected_date)
    )
    await state.set_state(BookingFSM.time)


@router.callback_query(BookingFSM.date, F.data == "booking_more_dates")
async def show_more_dates(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    service_duration = data.get('service_duration', 60)
    available_dates = await BookingService.get_available_dates(service_duration, days_ahead=21)
    await callback.message.edit_text(
        '📅 <b>Все доступные даты:</b>\n\nВыберите дату:',
        parse_mode='HTML',
        reply_markup=get_date_keyboard(available_dates, service_duration, show_more=True)
    )
    await state.set_state(BookingFSM.date)


@router.callback_query(BookingFSM.time, F.data == "booking_more_dates")
async def back_to_dates_from_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    service_duration = data.get('service_duration', 60)
    available_dates = await BookingService.get_available_dates(service_duration, days_ahead=21)
    await callback.message.edit_text(
        '📅 <b>Все доступные даты:</b>\n\nВыберите дату:',
        parse_mode='HTML',
        reply_markup=get_date_keyboard(available_dates, service_duration, show_more=True)
    )
    await state.set_state(BookingFSM.date)


@router.callback_query(BookingFSM.time, F.data.startswith("time_"))
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    time_str = callback.data.replace('time_', '')
    hours, minutes = map(int, time_str.split(':'))
    selected_time = time(hours, minutes)
    data = await state.get_data()
    selected_date = _to_date(data.get('selected_date'))  # конвертируем строку в date
    service = data.get('service', 'Услуга')
    service_duration = data.get('service_duration', 60)

    # Сохраняем время как строку!
    await state.update_data(selected_time=selected_time.strftime('%H:%M'))

    await callback.message.edit_text(
        '📋 <b>ПРОВЕРЬТЕ ДАННЫЕ:</b>\n\n'
        f'🦷 Услуга: <b>{service}</b>\n'
        f'📅 Дата: <b>{selected_date.strftime("%d.%m.%Y") if selected_date else "—"}</b>\n'
        f'🕐 Время: <b>{selected_time.strftime("%H:%M")}</b>\n'
        f'⏱ Длительность: <b>{service_duration} мин</b>\n\n'
        f'Всё верно?',
        parse_mode='HTML',
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(BookingFSM.confirm)


@router.callback_query(BookingFSM.confirm, F.data == "booking_confirm")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    telegram_id = callback.from_user.id

    try:
        selected_date = _to_date(data.get('selected_date'))
        selected_time = _to_time(data.get('selected_time'))

        if not selected_date or not selected_time:
            raise ValueError("Не выбрана дата или время")

        booking = await BookingService.book_slot(
            user_id=telegram_id,
            service=data.get('service', 'Услуга'),
            service_duration=data.get('service_duration', 60),
            booking_date=selected_date,
            booking_time=selected_time,
        )
        await AntiFraudService.update_score(telegram_id, 'booking')
        current_discount = await DiscountEngine.get_available_discount(telegram_id)

        await callback.message.edit_text(
            '✅ <b>ЗАПИСЬ ПОДТВЕРЖДЕНА!</b>\n\n'
            f'🦷 {booking.service}\n'
            f'📅 {booking.date.strftime("%d.%m.%Y")}\n'
            f'🕐 {booking.time.strftime("%H:%M")}\n\n'
            f'💎 Ваша скидка <b>{current_discount}%</b> заморожена до визита.\n'
            f'⏰ Напомним за 2 часа до приёма.',
            parse_mode='HTML',
            reply_markup=get_booking_success_keyboard()
        )
        await notify_admin_new_booking(callback, booking)

    except SlotBusyException as e:
        await callback.message.edit_text(
            f'⚠️ <b>Время занято!</b>\n\n{e.message}\n\nВыберите другое время:',
            parse_mode='HTML',
            reply_markup=get_alternative_keyboard(
                (e.alternative_date, e.alternative_time) if e.alternative_time else None
            )
        )
        await state.set_state(BookingFSM.time)
        return

    except Exception as e:
        logger.error(f'Ошибка бронирования: {e}')
        await callback.message.edit_text(
            '❌ <b>Ошибка записи!</b>\n\nПожалуйста, попробуйте позже.',
            parse_mode='HTML',
            reply_markup=get_main_menu_keyboard()
        )

    await state.clear()


@router.callback_query(BookingFSM.confirm, F.data == "booking_cancel")
async def cancel_booking_process(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        '❌ Запись отменена.\n\nВыберите услугу заново:',
        parse_mode='HTML',
        reply_markup=get_booking_services_keyboard()
    )


@router.callback_query(BookingFSM.confirm, F.data == "booking_add_comment")
async def add_comment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        '💬 <b>Введите комментарий к записи:</b>\n\n'
        '<i>Например: Болит зуб справа, Нужна консультация</i>\n\n'
        'Или нажмите /skip чтобы пропустить',
        parse_mode='HTML',
    )
    await state.set_state(BookingFSM.comment)


@router.message(BookingFSM.comment)
async def process_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text[:500])
    data = await state.get_data()
    selected_date = _to_date(data.get('selected_date'))
    selected_time = _to_time(data.get('selected_time'))

    await message.answer(
        '📋 <b>ПРОВЕРЬТЕ ДАННЫЕ:</b>\n\n'
        f'🦷 Услуга: <b>{data.get("service", "Услуга")}</b>\n'
        f'📅 Дата: <b>{selected_date.strftime("%d.%m.%Y") if selected_date else "—"}</b>\n'
        f'🕐 Время: <b>{selected_time.strftime("%H:%M") if selected_time else "—"}</b>\n'
        f'⏱ Длительность: <b>{data.get("service_duration", 60)} мин</b>\n'
        f'💬 Комментарий: <i>{message.text[:500]}</i>\n\n'
        f'Подтвердить запись?',
        parse_mode='HTML',
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(BookingFSM.confirm)


@router.callback_query(F.data.startswith("alt_accept_"))
async def accept_alternative(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data_part = callback.data.replace('alt_accept_', '')
    parts = data_part.rsplit('_', 1)
    alt_date = datetime.strptime(parts[0], '%Y-%m-%d').date()
    hours, minutes = map(int, parts[1].split('-'))
    alt_time = time(hours, minutes)
    data = await state.get_data()

    # Сохраняем строки
    await state.update_data(
        selected_date=alt_date.isoformat(),
        selected_time=alt_time.strftime('%H:%M')
    )

    await callback.message.edit_text(
        '📋 <b>ПРОВЕРЬТЕ ДАННЫЕ:</b>\n\n'
        f'🦷 Услуга: <b>{data.get("service", "Услуга")}</b>\n'
        f'📅 Дата: <b>{alt_date.strftime("%d.%m.%Y")}</b>\n'
        f'🕐 Время: <b>{alt_time.strftime("%H:%M")}</b>\n'
        f'⏱ Длительность: <b>{data.get("service_duration", 60)} мин</b>\n\n'
        f'Подтвердить запись?',
        parse_mode='HTML',
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(BookingFSM.confirm)


@router.callback_query(F.data == "alt_search_again")
async def search_again(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    selected_date = _to_date(data.get('selected_date'))
    service_duration = data.get('service_duration', 60)
    available_slots = await BookingService.get_available_slots(selected_date, service_duration)
    await callback.message.edit_text(
        f'📅 <b>{selected_date.strftime("%d.%m.%Y") if selected_date else "—"}</b>\n\nВыберите другое время:',
        parse_mode='HTML',
        reply_markup=get_time_keyboard(available_slots, selected_date)
    )
    await state.set_state(BookingFSM.time)


@router.callback_query(F.data == "booking_my")
async def show_my_bookings(callback: CallbackQuery):
    await callback.answer()
    bookings = await BookingService.get_user_bookings(callback.from_user.id)
    if not bookings:
        await callback.message.edit_text(
            '📅 <b>МОИ ЗАПИСИ</b>\n\n<i>У вас пока нет записей.</i>\n\nЗапишитесь прямо сейчас!',
            parse_mode='HTML',
            reply_markup=get_booking_services_keyboard()
        )
        return

    text = '📅 <b>МОИ ЗАПИСИ</b>\n\n'
    for b in bookings[:10]:
        status_emoji = {'confirmed': '✅', 'pending': '⏳', 'completed': '✔️', 'cancelled': '❌', 'rejected': '🚫'}.get(b.status, '❓')
        text += f'{status_emoji} <b>{b.date.strftime("%d.%m.%Y")}</b> {b.time.strftime("%H:%M")}\n   {b.service} ({b.duration} мин)\n   Статус: {b.status}\n\n'

    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=get_back_keyboard('menu_booking'))


async def notify_admin_new_booking(callback: CallbackQuery, booking):
    from config import settings
    admin_text = (
        f'⚡️ <b>НОВАЯ ЗАПИСЬ!</b>\n\n'
        f'👤 Пациент: {callback.from_user.full_name}\n'
        f'📱 Telegram ID: {callback.from_user.id}\n'
        f'🦷 Услуга: {booking.service}\n'
        f'📅 Дата: {booking.date.strftime("%d.%m.%Y")}\n'
        f'🕐 Время: {booking.time.strftime("%H:%M")}\n'
        f'⏱ Длительность: {booking.duration} мин\n'
    )
    if booking.comment:
        admin_text += f'💬 Комментарий: {booking.comment}\n'
    for admin_id in settings.SUPERADMINS + settings.ADMINS:
        try:
            await callback.bot.send_message(admin_id, admin_text, parse_mode='HTML')
        except Exception as e:
            logger.error(f'Не удалось отправить уведомление админу {admin_id}: {e}')
