from aiogram import types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


# Состояния FSM
class CryptoFSM(StatesGroup):
    crypto_currency = State()
    network = State()
    amount = State()
    contact = State()


# Клавиатура выбора криптовалюты
def get_crypto_currency_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="BTC"), KeyboardButton(text="ETH"), KeyboardButton(text="USDT")],
            [KeyboardButton(text="BNB"), KeyboardButton(text="XRP"), KeyboardButton(text="DOGE")],
            [KeyboardButton(text="ADA"), KeyboardButton(text="SOL"), KeyboardButton(text="TRX")],
            [KeyboardButton(text="🔍 Ввести вручную")]
        ],
        resize_keyboard=True
    )


# Клавиатура выбора сети
def get_network_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ERC20"), KeyboardButton(text="TRC20")],
            [KeyboardButton(text="BEP20"), KeyboardButton(text="Polygon")]
        ],
        resize_keyboard=True
    )


# Команда /crypto
async def start_crypto(message: types.Message, state: FSMContext):
    await message.answer("Выберите криптовалюту:", reply_markup=get_crypto_currency_keyboard())
    await state.set_state(CryptoFSM.crypto_currency)


# Выбор криптовалюты
async def get_crypto_currency(message: types.Message, state: FSMContext):
    await state.update_data(crypto_currency=message.text)
    if message.text == "🔍 Ввести вручную":
        await message.answer("Введите название криптовалюты вручную:")
        return
    await message.answer("Теперь выберите сеть:", reply_markup=get_network_keyboard())
    await state.set_state(CryptoFSM.network)


# Выбор сети
async def get_network(message: types.Message, state: FSMContext):
    await state.update_data(network=message.text)
    await message.answer("Введите сумму:")
    await state.set_state(CryptoFSM.amount)


# Ввод суммы
async def get_amount(message: types.Message, state: FSMContext):
    await state.update_data(amount=message.text)

    await message.answer(
        f"⚠️ Актуальный курс недоступен.\n\n"
        f"Предположим, вы получите ~XXX USD за {message.text} монет.\n"
        f"Точный расчет будет сделан оператором обменника."
    )

    await message.answer(
        "Отправьте криптовалюту на следующий адрес обменника:\n\n"
        "`7777777`\n\n"
        "После оплаты укажите ваш контакт для связи (номер телефона или Telegram).",
        parse_mode="Markdown"
    )

    await state.set_state(CryptoFSM.contact)


# Ввод контакта
async def get_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    data = await state.get_data()

    summary = "\n".join(f"{k.capitalize()}: {v}" for k, v in data.items())
    await message.answer(f"✅ Заявка на обмен принята:\n{summary}")
    await state.clear()


# Регистрация хендлеров
def register_crypto_handlers(dp: Dispatcher):
    dp.message.register(start_crypto, Command("crypto"))
    dp.message.register(get_crypto_currency, StateFilter(CryptoFSM.crypto_currency))
    dp.message.register(get_network, StateFilter(CryptoFSM.network))
    dp.message.register(get_amount, StateFilter(CryptoFSM.amount))
    dp.message.register(get_contact, StateFilter(CryptoFSM.contact))
