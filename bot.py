import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiohttp import web
import requests

# Конфигурация
TOKEN = '7735194034:AAHvaLquKVm4I1QpdjVx5J5YOCqlGAMJDBk'
ADMIN_ID = 7455246670
GROUP_ID = -1002554033993
WEBHOOK_URL = 'https://my-tg-bot-8mcp.onrender.com/webhook'  # URL вебхука

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилища
signals = {}  # {id: {"text": str, "users": [usernames]}}
usernames = {}  # user_id: username

# Состояния
class SignalStates(StatesGroup):
    waiting_for_signal_text = State()

# Установить вебхук
async def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    response = requests.post(url, data={"url": WEBHOOK_URL})
    print(response.json())

# Хендлеры
async def webhook(request):
    json_str = await request.json()  # Получаем JSON из запроса
    update = types.Update.parse_obj(json_str)  # Преобразуем в объект обновления
    await dp.process_update(update)  # Обрабатываем обновление через aiogram
    return web.Response()  # Возвращаем пустой ответ

# Клавиатуры
def admin_menu():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[ 
            [InlineKeyboardButton(text="💹 Выдать сигнал", callback_data="give_signal")],
            [InlineKeyboardButton(text="👥 Пользователи бота", callback_data="list_users")],
            [InlineKeyboardButton(text="📜 Список сигналов", callback_data="list_signals")]
        ]
    )
    return keyboard

def signals_list_keyboard():
    buttons = [
        [InlineKeyboardButton(text=signal["text"][:30], callback_data=f"signal_{signal_id}")]
        for signal_id, signal in signals.items()
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def signal_detail_keyboard(signal_id):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[ 
            [InlineKeyboardButton(text="🗑️ Удалить сигнал", callback_data=f"delete_signal_{signal_id}"),
             InlineKeyboardButton(text="👥 Кто зашел", callback_data=f"users_in_signal_{signal_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="list_signals")]
        ]
    )
    return keyboard

# Хендлеры для команд и колбеков
@dp.message(Command("start"))
async def start(message: types.Message):
    usernames[message.from_user.id] = message.from_user.username or message.from_user.full_name
    if message.from_user.id == ADMIN_ID:
        await message.answer("Добро пожаловать, админ!", reply_markup=admin_menu())
    else:
        await message.answer("Привет! Ожидай сигналы.")

@dp.callback_query(F.data == "give_signal")
async def give_signal(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите текст сигнала:", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]]
    ))
    await state.set_state(SignalStates.waiting_for_signal_text)

@dp.message(SignalStates.waiting_for_signal_text)
async def save_signal_text(message: types.Message, state: FSMContext):
    signal_id = str(len(signals) + 1)
    signals[signal_id] = {"text": message.text, "users": []}

    # Отправляем сигнал в группу с кнопкой
    await bot.send_message(GROUP_ID, f"📊 Новый сигнал!",
                            reply_markup=InlineKeyboardMarkup(
                                inline_keyboard=[[InlineKeyboardButton(text="Получить сигнал", callback_data=f"join_{signal_id}")]]
                            ))

    # Рассылка сигнала всем пользователям бота
    for user_id in usernames:
        await bot.send_message(user_id, f"📊 Новый сигнал! Нажмите кнопку, чтобы получить сигнал.",
                               reply_markup=InlineKeyboardMarkup(
                                   inline_keyboard=[[InlineKeyboardButton(text="Получить сигнал", callback_data=f"join_{signal_id}")]]
                               ))

    await message.answer("Сигнал создан и расслан!", reply_markup=admin_menu())
    await state.clear()

# Прочие колбек-хендлеры...
# (Оставляем все остальные хендлеры без изменений, как в вашем исходном коде)

# Запуск сервера с вебхуками
async def on_start(request):
    return web.Response(text="Бот работает!")

async def main():
    # Устанавливаем вебхук при запуске
    await set_webhook()

    # Настройка веб-сервера
    app = web.Application()
    app.router.add_get('/', on_start)  # Главная страница
    app.router.add_post('/webhook', webhook)  # Обработка вебхуков от Telegram

    # Получаем порт из переменной окружения
    port = int(os.environ.get("PORT", 8080))  # Если переменная не задана, используется порт 8080
    print(f"Сервер запущен на порту {port}")

    # Запуск сервера
    await web._run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(main())
