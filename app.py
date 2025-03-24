from flask import Flask, request, jsonify
import json
import os
import hashlib

app = Flask(__name__)

# Путь к файлу, где будут храниться данные пользователей
USER_DB_FILE = 'users.json'

# Загружаем пользователей из файла, если файл существует
def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

# Сохраняем пользователей в файл
def save_users(users):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f)

# Хешируем пароль с использованием SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Проверка пин-кода (например, "1312")
def check_pin(pin_code):
    correct_pin = "f16721a7b9105dca050e3c73b816bc3ce1b3f7a2bc5078f0c3a62fe5ff26fecc"
    return pin_code == correct_pin

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    pin_code = request.form.get("pin")

    # Проверяем правильность пин-кода
    if not check_pin(pin_code):
        return jsonify({"message": "Неверный пин-код!"}), 400

    users = load_users()

    if username in users:
        return jsonify({"message": "Пользователь уже существует!"}), 400

    if not password:
        return jsonify({"message": "Пароль не может быть пустым!"}), 400

    # Сохраняем пользователя с хешированным паролем (без пин-кода)
    users[username] = {'password': hash_password(password)}
    save_users(users)
    return jsonify({"message": "Регистрация успешна!"}), 200

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    users = load_users()

    if username not in users or users[username]['password'] != hash_password(password):
        return jsonify({"message": "Неверный логин или пароль."}), 400

    return jsonify({"message": "Вход успешен!"}), 200

if __name__ == "__main__":
    app.run(debug=True)
