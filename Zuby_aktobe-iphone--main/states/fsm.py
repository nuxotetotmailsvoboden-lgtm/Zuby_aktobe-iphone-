from aiogram.fsm.state import State, StatesGroup


class RegistrationFSM(StatesGroup):
    """Состояния регистрации нового пользователя"""
    first_name = State()
    last_name = State()
    phone = State()
    instagram = State()


class BookingFSM(StatesGroup):
    """Состояния записи на приём"""
    service = State()
    date = State()
    time = State()
    comment = State()
    confirm = State()


class ContentFSM(StatesGroup):
    """Состояния отправки контента"""
    content_type = State()
    link = State()


class BroadcastFSM(StatesGroup):
    """Состояния рассылки"""
    segment = State()
    message = State()
    confirm = State()
