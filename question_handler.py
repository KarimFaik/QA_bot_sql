import sqlite3
import os
import re
from pymorphy3 import MorphAnalyzer
from synonyms import synonyms

# Инициализация морфологического анализатора
morph = MorphAnalyzer()

# Путь к базе данных (в папке Data)
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Data", "data.db")

# Лемматизация текста
def lemmatize_text(text):
    words = re.findall(r'\w+', text.lower())
    return ' '.join([morph.parse(word)[0].normal_form for word in words])

# Поиск ключевых слов в вопросе
def find_keywords_in_question(question):
    lemmatized_question = lemmatize_text(question)
    keywords = []

    # Ищем основное ключевое слово и второе ключевое слово
    for primary_keyword, synonym_list in synonyms.items():
        # Проверяем основное ключевое слово
        if lemmatize_text(primary_keyword) in lemmatized_question:
            keywords.append(primary_keyword)
        
        # Проверяем синонимы основного ключевого слова
        for synonym in synonym_list:
            if lemmatize_text(synonym) in lemmatized_question:
                keywords.append(primary_keyword)
                break  # Прерываем цикл, если синоним найден

    return keywords

# Поиск ответа в базе данных
def find_answer_in_db(question):
    if not os.path.exists(db_path):
        return None, ["База данных не найдена."]

    lemmatized_question = lemmatize_text(question)
    flags = []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    keywords = find_keywords_in_question(question)
    if not keywords:
        flags.append("Ключевые слова не найдены в вопросе.")
        conn.close()
        return None, flags

    answers = []
    for keyword in keywords:
        cursor.execute('''
            SELECT answer, secondary_keyword FROM data
            WHERE primary_keyword = ?
        ''', (keyword,))
        results = cursor.fetchall()

        if results:
            flags.append(f"Найдены ответы по ключевому слову: {keyword}")
            # Фильтруем некорректные ответы (например, односимвольные)
            valid_results = [(ans, sec) for ans, sec in results if len(ans.strip()) > 1]
            answers.extend(valid_results)

    conn.close()

    if not answers:
        flags.append("Ответы не найдены или отфильтрованы как некорректные.")
        return None, flags

    if len(answers) > 1:
        for answer, secondary_keyword in answers:
            if secondary_keyword and lemmatize_text(secondary_keyword) in lemmatized_question:
                flags.append(f"Найдено вторичное ключевое слово: {secondary_keyword}")
                return [(answer, secondary_keyword)], flags

        flags.append("Вторичное ключевое слово не найдено, возвращаем все ответы.")
        return answers, flags
    else:
        flags.append("Найдено одно совпадение, возвращаем ответ.")
        return [(answers[0][0], answers[0][1])], flags