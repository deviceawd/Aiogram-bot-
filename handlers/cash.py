from aiogram import types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
from keyboards import get_city_keyboard, get_time_keyboard


# 💼 Состояния FSM
class CashFSM(StatesGroup):
    currency = State()
    amount = State()
    city = State()
    time = State()
    name = State()
    phone = State()


# 🔁 Хендлеры поэтапно
async def start_cash(message: types.Message, state: FSMContext):
    await message.answer(
        "Выберите валюту:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="USD"), types.KeyboardButton(text="EUR")]],
            resize_keyboard=True
        )
    )
    await state.set_state(CashFSM.currency)


async def get_currency(message: types.Message, state: FSMContext):
    await state.update_data(currency=message.text)
    await message.answer("Введите сумму:")
    await state.set_state(CashFSM.amount)


async def get_amount(message: types.Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await message.answer("Выберите город и отделение:", reply_markup=get_city_keyboard())
    await state.set_state(CashFSM.city)


async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Выберите удобное время визита:", reply_markup=get_time_keyboard())
    await state.set_state(CashFSM.time)


async def get_time(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer("Введите имя:")
    await state.set_state(CashFSM.name)


async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите номер телефона:")
    await state.set_state(CashFSM.phone)


async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    summary = "\n".join(f"{k.capitalize()}: {v}" for k, v in data.items())
    await message.answer(f"✅ Заявка получена:\n\n{summary}")
    await state.clear()


# 🔧 Регистрация хендлеров
def register_cash_handlers(dp: Dispatcher):
    dp.message.register(start_cash, Command("cash"))
    dp.message.register(get_currency, StateFilter(CashFSM.currency))
    dp.message.register(get_amount, StateFilter(CashFSM.amount))
    dp.message.register(get_city, StateFilter(CashFSM.city))
    dp.message.register(get_time, StateFilter(CashFSM.time))
    dp.message.register(get_name, StateFilter(CashFSM.name))
    dp.message.register(get_phone, StateFilter(CashFSM.phone))
