import sqlite3
import os

# Загрузка текста из файла
def load_text():
    # Указываем путь к файлу напрямую
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"Data", "Data.txt")
    
    try:
        with open(data_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Файл {data_path} не найден.")
        return None

# Парсинг текста в структурированные данные
def parse_text(text):
    data = []
    lines = text.strip().split("\n")  # Разделяем текст на строки
    
    for line in lines:
        # Разделяем строку на ключевые слова и ответ
        if "," in line:
            parts = line.split(",", 2)  # Разделяем по первой и второй запятой
            if len(parts) == 3:
                primary_keyword = parts[0].strip()
                secondary_keyword = parts[1].strip()
                answer = parts[2].strip()
                data.append((primary_keyword, secondary_keyword, answer))
            else:
                print(f"Некорректный формат строки: {line}")
        else:
            print(f"Некорректный формат строки: {line}")
    
    return data

# Создание базы данных и таблицы
def create_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            primary_keyword TEXT NOT NULL,
            secondary_keyword TEXT,
            answer TEXT NOT NULL,
            UNIQUE(primary_keyword, secondary_keyword)  -- Уникальность комбинации ключевых слов
        )
    ''')
    conn.commit()
    return conn

# Вставка данных в базу данных
def insert_data(conn, primary_keyword, secondary_keyword, answer):
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO data (primary_keyword, secondary_keyword, answer)
            VALUES (?, ?, ?)
        ''', (primary_keyword, secondary_keyword, answer))
        conn.commit()
        print(f"Данные добавлены: {primary_keyword}, {secondary_keyword}")
    except sqlite3.IntegrityError:
        print(f"Данные уже существуют: {primary_keyword}, {secondary_keyword}")

# Основная функция
def main():
    # Загрузка текста из файла
    text = load_text()
    if not text:
        return
    
    # Парсинг текста в структурированные данные
    data = parse_text(text)
    if not data:
        print("Нет данных для вставки в базу данных.")
        return
    
    # Создание базы данных
    conn = create_db('data.db')
    
    # Вставка данных
    for primary_keyword, secondary_keyword, answer in data:
        insert_data(conn, primary_keyword, secondary_keyword, answer)
    
    # Закрытие соединения
    conn.close()
    print("Данные успешно загружены в базу данных.")

if __name__ == "__main__":
    main()