from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

def get_network_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="TRC20 (Tron)", callback_data="TRC20")],
        [InlineKeyboardButton(text="ERC20 (Ethereum)", callback_data="ERC20")]
    ])
    return kb

def get_city_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Киев")],
        [KeyboardButton(text="Харьков")],
        [KeyboardButton(text="Львов")]
    ], resize_keyboard=True)

def get_time_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Сегодня"), KeyboardButton(text="Завтра")],
        [KeyboardButton(text="Через 2 дня")]
    ], resize_keyboard=True)
