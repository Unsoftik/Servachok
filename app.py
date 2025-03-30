from flask import Flask, request, jsonify
import json
import os
import hashlib

app = Flask(__name__)

USER_DB_FILE = 'users.json'
PROTOCOL_STATE_FILE = 'protocol_state.json'

# Загружаем пользователей из файла
def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

# Сохраняем пользователей в файл
def save_users(users):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f)

# Загружаем состояние протокола
def load_protocol_state():
    if os.path.exists(PROTOCOL_STATE_FILE):
        with open(PROTOCOL_STATE_FILE, 'r') as f:
            return json.load(f).get('zero_protocol', False)
    return False

# Сохраняем состояние протокола
def save_protocol_state(state):
    with open(PROTOCOL_STATE_FILE, 'w') as f:
        json.dump({'zero_protocol': state}, f)

# Хешируем пароль с использованием SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Проверка пин-кода (теперь без хеширования)
def check_pin(pin_code):
    correct_pin = "1312"  # Сравниваем напрямую как строку
    return pin_code == correct_pin

# Включение нулевого протокола
@app.route("/activate_zero_protocol", methods=["POST"])
def activate_zero_protocol():
    pin_code = request.form.get("pin")
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    save_protocol_state(True)
    return jsonify({"message": "Нулевой протокол активирован!"}), 200

# Выключение нулевого протокола
@app.route("/deactivate_zero_protocol", methods=["POST"])
def deactivate_zero_protocol():
    pin_code = request.form.get("pin")
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    save_protocol_state(False)
    return jsonify({"message": "Нулевой протокол деактивирован!"}), 200

# Регистрация
@app.route("/register", methods=["POST"])
def register():
    if load_protocol_state():
        return jsonify({"message": "Zero protocol activated"}), 403
    
    username = request.form.get("username")
    password = request.form.get("password")
    pin_code = request.form.get("pin")
    
    # Отладка: вывод полученных данных
    print(f"Получено: username={username}, password={password}, pin={pin_code}")
    
    if not pin_code:
        return jsonify({"message": "Пин-код отсутствует!"}), 400
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400
    
    users = load_users()
    if username in users:
        return jsonify({"message": "Пользователь уже существует!"}), 400
    if not username:
        return jsonify({"message": "Имя пользователя отсутствует!"}), 400
    if not password:
        return jsonify({"message": "Пароль не может быть пустым!"}), 400
    
    users[username] = {'password': hash_password(password)}
    save_users(users)
    return jsonify({"message": "Регистрация успешна!"}), 200

# Вход
@app.route("/login", methods=["POST"])
def login():
    if load_protocol_state():
        return jsonify({"message": "Zero protocol activated"}), 403
    
    username = request.form.get("username")
    password = request.form.get("password")
    
    users = load_users()
    if username not in users or users[username]['password'] != hash_password(password):
        return jsonify({"message": "Неверный логин или пароль."}), 400
    
    return jsonify({"message": "Вход успешен!"}), 200

# Проверка разработчика (пример)
@app.route("/check_developer", methods=["GET"])
def check_developer():
    if load_protocol_state():
        return jsonify({"message": "Zero protocol activated"}), 403
    return jsonify({"message": "Проверка разработчика"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
