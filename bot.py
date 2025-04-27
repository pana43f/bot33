import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# Конфигурация
TOKEN = '7735194034:AAHvaLquKVm4I1QpdjVx5J5YOCqlGAMJDBk'
ADMIN_ID = 7455246670
GROUP_ID = -1002554033993

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилища
signals = {}  # {id: {"text": str, "users": [usernames]}}
usernames = {}  # user_id: username


# Состояния
class SignalStates(StatesGroup):
    waiting_for_signal_text = State()


# --- Клавиатуры ---
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
            [
                InlineKeyboardButton(text="🗑️ Удалить сигнал", callback_data=f"delete_signal_{signal_id}"),
                InlineKeyboardButton(text="👥 Кто зашел", callback_data=f"users_in_signal_{signal_id}")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="list_signals")]
        ]
    )
    return keyboard


# --- Хендлеры ---
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


@dp.callback_query(F.data == "list_users")
async def list_users(callback: types.CallbackQuery):
    if usernames:
        text = "👥 Пользователи бота:\n" + "\n".join([f"- {name}" for name in usernames.values()])
    else:
        text = "Пока нет пользователей."

    await callback.message.edit_text(text, reply_markup=admin_menu())


@dp.callback_query(F.data == "list_signals")
async def list_signals(callback: types.CallbackQuery):
    if signals:
        await callback.message.edit_text("📜 Список сигналов:", reply_markup=signals_list_keyboard())
    else:
        await callback.message.edit_text("Нет активных сигналов.", reply_markup=admin_menu())


@dp.callback_query(F.data.startswith("signal_"))
async def show_signal_details(callback: types.CallbackQuery):
    signal_id = callback.data.split("_")[1]
    signal = signals.get(signal_id)

    if signal:
        text = f"📊 Сигнал:\n\n{signal['text']}"
        await callback.message.edit_text(text, reply_markup=signal_detail_keyboard(signal_id))
    else:
        await callback.message.edit_text("Сигнал не найден.", reply_markup=admin_menu())


@dp.callback_query(F.data.startswith("join_"))
async def join_signal(callback: types.CallbackQuery):
    signal_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.full_name

    # Проверка, получил ли пользователь уже сигнал
    if signal_id in signals and username not in signals[signal_id]["users"]:
        # Добавляем пользователя в список пользователей, которые присоединились к сигналу
        signals[signal_id]["users"].append(username)

        # Отправляем сам сигнал в личку пользователю
        await bot.send_message(user_id, f"📊 Ваш сигнал:\n\n{signals[signal_id]['text']}")

        # Уведомление о получении сигнала
        await bot.send_message(user_id, "✅ Вы уже получили сигнал. Больше не можете получить его повторно.")
    else:
        # Если пользователь уже получил сигнал
        await bot.send_message(user_id, "🚫 Вы уже получили этот сигнал и не можете получить его повторно.")

    # Блокируем дальнейшие попытки получить этот сигнал
    await callback.answer()


@dp.callback_query(F.data.startswith("delete_signal_"))
async def delete_signal(callback: types.CallbackQuery):
    signal_id = callback.data.split("_")[2]
    if signal_id in signals:
        del signals[signal_id]
    await callback.message.edit_text("Сигнал удалён.", reply_markup=admin_menu())


@dp.callback_query(F.data.startswith("users_in_signal_"))
async def users_in_signal(callback: types.CallbackQuery):
    signal_id = callback.data.split("_")[3]
    if signal_id in signals:
        users = signals[signal_id]["users"]
        text = "👥 Зашедшие в сигнал:\n" + "\n".join([f"- {user}" for user in users]) if users else "Пока никто не зашел."
        await callback.message.edit_text(text, reply_markup=signal_detail_keyboard(signal_id))
    else:
        await callback.message.edit_text("Сигнал не найден.", reply_markup=admin_menu())


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("Меню администратора:", reply_markup=admin_menu())


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
