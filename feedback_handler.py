import json
import os
from question_handler import find_answer_in_db, lemmatize_text
from synonyms import synonyms

# Путь к файлам (в папке Data)
SUCCESSFUL_ANSWERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Data", "successful_answers.json")
UNSUCCESSFUL_ANSWERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Data", "unsuccessful_answers.json")

# Загрузка деревьев ответов из файлов
def load_tree(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():  # Если файл пустой
                return {}
            return json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"Ошибка: файл {filename} содержит некорректный JSON.")
        return {}

# Сохранение деревьев ответов в файлы
def save_tree(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Дерево успешных ответов
successful_answers = load_tree(SUCCESSFUL_ANSWERS_FILE)

# Дерево неудачных ответов
unsuccessful_answers = load_tree(UNSUCCESSFUL_ANSWERS_FILE)

# Сохранение успешного ответа
def save_successful_answer(question, answer):
    lemmatized_question = lemmatize_text(question)
    successful_answers[lemmatized_question] = answer
    save_tree(SUCCESSFUL_ANSWERS_FILE, successful_answers)

# Сохранение неудачного ответа
def save_unsuccessful_answer(question, answer):
    lemmatized_question = lemmatize_text(question)
    if lemmatized_question not in unsuccessful_answers:
        unsuccessful_answers[lemmatized_question] = []
    unsuccessful_answers[lemmatized_question].append(answer)
    save_tree(UNSUCCESSFUL_ANSWERS_FILE, unsuccessful_answers)

# Поиск успешного ответа
def find_successful_answer(question):
    lemmatized_question = lemmatize_text(question)
    return successful_answers.get(lemmatized_question)

# Поиск неудачных ответов
def find_unsuccessful_answers(question):
    lemmatized_question = lemmatize_text(question)
    return unsuccessful_answers.get(lemmatized_question, [])

# Проверка, является ли ответ неправильным
def is_answer_unsuccessful(question, answer):
    unsuccessful_answers_for_question = find_unsuccessful_answers(question)
    return answer in unsuccessful_answers_for_question

# Обработка обратной связи
async def handle_feedback(update, context):
    feedback = update.message.text.lower()
    question = context.user_data.get("current_question")
    current_answer = context.user_data.get("current_answer")

    # Проверяем, что ответ не является сообщением об ошибке
    if current_answer == "Извините, я не могу найти ответ на ваш вопрос.":
        await update.message.reply_text("Этот ответ не может быть сохранён как успешный.")
        context.user_data["awaiting_feedback"] = False  # Сбрасываем состояние
        return

    if feedback == "да":
        # Сохраняем ответ в дерево успешных ответов
        save_successful_answer(question, current_answer)
        await update.message.reply_text("Спасибо за обратную связь! Рад, что смог помочь.")
        context.user_data["awaiting_feedback"] = False  # Сбрасываем состояние
    elif feedback == "нет":
        # Сохраняем ответ в дерево неудачных ответов
        save_unsuccessful_answer(question, current_answer)
        # Предлагаем следующий ответ
        await send_next_answer(update, context)
    else:
        # Если ответ не "Да" или "Нет"
        await update.message.reply_text("Пожалуйста, ответьте 'Да' или 'Нет'.")
        # Повторно запрашиваем обратную связь
        await update.message.reply_text("Ответил ли я на ваш вопрос? (Да/Нет)")

# Предложение следующего ответа
async def send_next_answer(update, context):
    question = context.user_data.get("current_question")
    answers = find_answer_in_db(question)  # Ищем ответы в базе данных

    if not answers:
        await update.message.reply_text("Извините, я не смог найти подходящий ответ. Пожалуйста, обратитесь к администратору.")
        context.user_data["awaiting_feedback"] = False  # Сбрасываем состояние
        return

    for answer in answers:
        answer_text = answer[0]  # Ответ из базы данных
        # Проверяем, не был ли ответ уже отклонен
        if not is_answer_unsuccessful(question, answer_text):
            context.user_data["current_answer"] = answer_text
            await update.message.reply_text(answer_text)
            await update.message.reply_text("Ответил ли я на ваш вопрос? (Да/Нет)")
            context.user_data["awaiting_feedback"] = True  # Устанавливаем состояние ожидания
            return

    # Если больше нет ответов
    await update.message.reply_text("Извините, я не смог найти подходящий ответ. Пожалуйста, обратитесь к администратору.")
    context.user_data["awaiting_feedback"] = False  # Сбрасываем состояние