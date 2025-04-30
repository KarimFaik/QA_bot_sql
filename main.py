import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from question_handler import find_answer_in_db, lemmatize_text
from feedback_handler import handle_feedback, find_successful_answer
from synonyms import synonyms
from transformer_handler import generate_answer_with_transformer

# Настройка логгера
logging.basicConfig( 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных из .env
load_dotenv()

# Токен бота
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Функция для записи логов в файл
def log_failure(question, flags):
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"Вопрос: {question}\n")
        f.write(f"Флаги: {flags}\n")
        f.write("-" * 40 + "\n")  # Разделитель для удобства чтения

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.message.from_user.username} запустил бота.")
    await update.message.reply_text(
        "Привет! Я бот для ответов на вопросы. Задайте мне вопрос, и я постараюсь помочь."
    )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    question = update.message.text
    logger.info(f"Пользователь {user.username} задал вопрос: {question}")

    if context.user_data.get("awaiting_feedback", False):
        await handle_feedback(update, context)
        return

    successful_answer = find_successful_answer(question)
    if successful_answer:
        await update.message.reply_text(successful_answer)
        return

    answers, flags = find_answer_in_db(question)
    if answers:
        if len(answers) > 1:
            # Уточняем у пользователя, если найдено несколько ответов
            '''options = [f"{i + 1}. {answer[1] if answer[1] else 'Общий ответ'}" for i, answer in enumerate(answers)]
            await update.message.reply_text(
                "Уточните, пожалуйста:\n" + "\n".join(options)
            )'''
            context.user_data["current_question"] = question
            context.user_data["current_answers"] = answers
            context.user_data["awaiting_clarification"] = True
        else:
            # Возвращаем единственный ответ
            context.user_data["current_question"] = question
            context.user_data["current_answer"] = answers[0][0]  # Берем текст ответа
            await update.message.reply_text(answers[0][0])
            await update.message.reply_text("Ответил ли я на ваш вопрос? (Да/Нет)")
            context.user_data["awaiting_feedback"] = True
    else:
        synonym_answers_found = False
        for keyword, synonym_list in synonyms.items():
            if lemmatize_text(question) in synonym_list:
                answers, _ = find_answer_in_db(keyword)
                if answers:
                    synonym_answers_found = True
                    context.user_data["current_question"] = question
                    context.user_data["current_answer"] = answers[0][0]
                    await update.message.reply_text(answers[0][0])
                    await update.message.reply_text("Ответил ли я на ваш вопрос? (Да/Нет)")
                    context.user_data["awaiting_feedback"] = True
                    return

        if not synonym_answers_found:
            log_failure(question, flags)
            await update.message.reply_text("Извините, я не могу найти ответ на ваш вопрос.\nОбратитесь к salpagarov-si@rudn.ru")
            context.user_data["awaiting_feedback"] = False
            '''context_for_transformer = "Ваш контекст для трансформера"
            transformer_answer = generate_answer_with_transformer(question, context_for_transformer)
            
            if transformer_answer:
                context.user_data["current_question"] = question
                context.user_data["current_answer"] = transformer_answer
                await update.message.reply_text(transformer_answer)
                await update.message.reply_text("Ответил ли я на ваш вопрос? (Да/Нет)")
                context.user_data["awaiting_feedback"] = True
            else:
                log_failure(question, flags)
                await update.message.reply_text("Извините, я не могу найти ответ на ваш вопрос.\nОбратитесь к salpagarov-si@rudn.ru")
                context.user_data["awaiting_feedback"] = False'''
            
# Обработчик ошибок
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка в обновлении {update}: {context.error}")

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