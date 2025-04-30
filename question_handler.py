import sqlite3
import os
import re
from pymorphy3 import MorphAnalyzer
from synonyms import synonyms


# Инициализация морфологического анализатора
morph = MorphAnalyzer()

# Путь к базе данных
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Data", "data.db")


def lemmatize_text(text):
    """
    Лемматизация текста — приведение слов к нормальной форме.
    """
    words = re.findall(r'\w+', text.lower())
    return ' '.join([morph.parse(word)[0].normal_form for word in words])


def find_keywords_in_question(question):
    """
    Поиск ключевых слов в вопросе, учитывая синонимы.
    """
    lemmatized_question = lemmatize_text(question)
    keywords = []

    for primary_keyword, synonym_list in synonyms.items():
        if lemmatize_text(primary_keyword) in lemmatized_question:
            keywords.append(primary_keyword)

        for synonym in synonym_list:
            if lemmatize_text(synonym) in lemmatized_question:
                keywords.append(primary_keyword)
                break  # Прерываем при первом совпадении

    return list(set(keywords))  # Удаляем дубликаты


def find_answer_in_db(question):
    """
    Основная функция поиска ответа в базе данных.
    """
    if not os.path.exists(db_path):
        return None, ["База данных не найдена."]

    lemmatized_question = lemmatize_text(question)
    print(f"[DEBUG] Лемматизированный вопрос: {lemmatized_question}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    keywords = find_keywords_in_question(question)
    answers = []
    flags = []

    if not keywords:
        flags.append("Не найдено ключевых слов.")
        return None, flags

    for keyword in keywords:
        # Гибкий запрос через LIKE
        cursor.execute('''
            SELECT answer, secondary_keyword FROM data
            WHERE primary_keyword LIKE ?
               OR secondary_keyword LIKE ?
        ''', (f"%{keyword}%", f"%{keyword}%"))
        results = cursor.fetchall()

        if results:
            valid_results = [(ans, sec) for ans, sec in results if len(ans.strip()) > 1]
            answers.extend(valid_results)
            flags.append(f"Найдены ответы по ключевому слову: {keyword}")

    conn.close()

    if not answers:
        flags.append("Ответов не найдено или они были отфильтрованы.")
        return None, flags

    # Фильтруем ответы по вторичному ключевому слову
    best_answers = []
    for answer, secondary in answers:
        if secondary and lemmatize_text(secondary) in lemmatized_question:
            best_answers.append((answer, secondary))
            flags.append(f"Выбран ответ по вторичному ключевому слову: {secondary}")
            break  # Берём первый подходящий ответ

    if best_answers:
        return best_answers, flags

    # Если вторичных ключевых слов нет — возвращаем первый ответ
    flags.append("Вторичные ключевые слова не соответствуют. Возвращаем первый ответ.")
    return [answers[0]], flags