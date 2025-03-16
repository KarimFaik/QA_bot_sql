import sqlite3
import os
import re
from pymorphy3 import MorphAnalyzer
from synonyms import synonyms

# Инициализация морфологического анализатора
morph = MorphAnalyzer()

# Путь к базе данных
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")

# Проверка существования таблицы
def check_table_exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data'")
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except sqlite3.Error as e:
        print(f"Ошибка при проверке таблицы: {e}")
        return False

# Загрузка данных из базы данных
def load_data(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT primary_keyword, secondary_keyword, answer FROM data')
        data = cursor.fetchall()
        conn.close()
        return data
    except sqlite3.Error as e:
        print(f"Ошибка при загрузке данных: {e}")
        return None

# Лемматизация текста
def lemmatize_text(text):
    words = re.findall(r'\w+', text.lower())
    return ' '.join([morph.parse(word)[0].normal_form for word in words])

# Поиск ключевых слов в вопросе
def find_keywords(question, data):
    lemmatized_question = lemmatize_text(question)
    
    # Сначала ищем основное ключевое слово
    primary_matches = []
    for primary_keyword, secondary_keyword, answer in data:
        # Проверяем основное ключевое слово
        if lemmatize_text(primary_keyword) in lemmatized_question:
            primary_matches.append((primary_keyword, secondary_keyword, answer))
            print(f"Найдено ключевое слово: {primary_keyword}")
        
        # Проверяем синонимы основного ключевого слова
        for synonym in synonyms.get(primary_keyword, []):
            if lemmatize_text(synonym) in lemmatized_question:
                primary_matches.append((primary_keyword, secondary_keyword, answer))
                print(f"Найден синоним: {synonym} для ключевого слова: {primary_keyword}")
    
    # Если основное ключевое слово найдено
    if primary_matches:
        # Если найдено несколько совпадений, проверяем вторичное ключевое слово
        if len(primary_matches) > 1:
            for primary_keyword, secondary_keyword, answer in primary_matches:
                if secondary_keyword and lemmatize_text(secondary_keyword) in lemmatized_question:
                    print(f"Найдено вторичное ключевое слово: {secondary_keyword}")
                    return answer
            # Если вторичное ключевое слово не найдено, возвращаем первый ответ
            return primary_matches[0][2]
        else:
            # Если совпадение одно, возвращаем его
            return primary_matches[0][2]
    
    # Если ничего не найдено
    return None

# Основная функция для поиска ответа
def get_answer(question):
    # Проверка существования таблицы
    if not check_table_exists(db_path):
        return "Таблица 'data' не найдена в базе данных."
    
    # Загрузка данных
    data = load_data(db_path)
    if not data:
        return "База данных пуста. Пожалуйста, добавьте данные."
    
    # Поиск ответа
    answer = find_keywords(question, data)
    if answer:
        return answer
    else:
        return "Извините, я не могу найти ответ на ваш вопрос."