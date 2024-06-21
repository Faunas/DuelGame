import sqlparse
import json

def extract_insert_words(sql_file_path):
    with open(sql_file_path, 'r', encoding='utf-8') as file:
        sql_script = file.read()

    parsed = sqlparse.parse(sql_script)
    insert_words = []

    for statement in parsed:
        if statement.get_type() == 'INSERT':
            # Используем регулярное выражение для извлечения значений в скобках
            values = sqlparse.sql.IdentifierList(statement).get_identifiers()
            for value in values:
                word = value.get_parent().value.strip("(),'\"")
                insert_words.append(word)

    return insert_words

# Путь к вашему SQL файлу
sql_file_path = 'words-russian-nouns.sql'

# Извлекаем слова из команд INSERT INTO
insert_words = extract_insert_words(sql_file_path)

# Сохраняем данные в JSON файл
json_file_path = 'insert_words.json'
with open(json_file_path, 'w', encoding='utf-8') as json_file:
    json.dump(insert_words, json_file, ensure_ascii=False, indent=4)

print(f"Данные успешно сохранены в файл {json_file_path}")
