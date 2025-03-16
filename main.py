import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from model import get_answer  # Импорт функции для поиска ответа

# Настройка логгера
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных из .env
load_dotenv()

# Токен бота
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.message.from_user.username} started the bot.")
    await update.message.reply_text(
        "Привет! Я бот для ответов на вопросы. Задайте мне вопрос, и я постараюсь помочь."
    )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    question = update.message.text
    logger.info(f"User {user.username} asked: {question}")

    # Получаем ответ
    answer = get_answer(question)
    
    # Логируем успешный запрос
    logger.info(f"Status 200: Ответ для пользователя {user.username} отправлен.")
    
    # Отправляем ответ пользователю
    await update.message.reply_text(answer)

# Обработчик ошибок
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}")

# Основная функция
def main():
    # Создаем приложение для бота
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Регистрируем обработчик ошибок
    app.add_error_handler(error)

    # Запускаем бота
    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()